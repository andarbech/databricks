"""Opt-in integration tests against Lakebase; temporary committed data is removed."""
import os
import unittest
from unittest.mock import patch
from sqlalchemy import text
from app import app
from lakebase import get_engine

@unittest.skipUnless(os.environ.get('LAKEBASE_ENDPOINT'), 'Set LAKEBASE_ENDPOINT and authenticate with OAuth')
class SupportAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.engine = get_engine()

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def test_validation(self):
        for payload in ({}, [], {'title': ' '}, {'title': 'x' * 201}, {'title': None}, {'title': 'a\x00b'}, {'title': 'Valid', 'created_by': 'forged@example.com'}):
            self.assertEqual(self.client.post('/tickets', json=payload).status_code, 400)
        self.assertEqual(self.client.post('/tickets', data='not json').status_code, 415)
        self.assertEqual(self.client.post('/tickets', data='{', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post('/tickets', data='x'*70000, content_type='application/json').status_code, 413)
        for payload in ({}, [], {'status': 'invalid'}, {'status': []}, {'status': 'open', 'title': 'Ignored'}):
            self.assertEqual(self.client.patch('/tickets/3', json=payload).status_code, 400)
        for payload in ({}, [], {'message_text': ' '}, {'message_text': 'x'*10001}, {'message_text': 'Valid', 'author': 'forged@example.com'}):
            self.assertEqual(self.client.post('/tickets/3/messages', json=payload).status_code, 400)
        with patch.dict(os.environ, {'DATABRICKS_APP_NAME': 'test-app'}):
            self.assertEqual(self.client.post('/tickets', json={'title':'Test'}).status_code, 401)
            self.assertEqual(self.client.patch('/tickets/3', json={'status':'open'}).status_code, 401)
            self.assertEqual(self.client.post('/tickets/3/messages', json={'message_text':'Test'}).status_code, 401)

    def test_missing_ticket(self):
        path = '/tickets/9223372036854775807'
        self.assertEqual(self.client.get(path+'/messages').status_code, 404)
        self.assertEqual(self.client.post(path+'/messages', json={'message_text':'Test'}).status_code, 404)
        self.assertEqual(self.client.patch(path, json={'status':'resolved'}).status_code, 404)
        self.assertEqual(self.client.patch('/tickets/0', json={'status':'open'}).status_code, 400)

    def test_complete_workflow_and_persistence(self):
        ticket_id = None
        with self.engine.connect() as connection:
            before = connection.execute(text('SELECT (SELECT count(*) FROM support_app.tickets), (SELECT count(*) FROM support_app.ticket_messages)')).one()
        try:
            response = self.client.post('/tickets', json={'title':"  Integration check: <script>alert('test')</script>  "})
            self.assertEqual(response.status_code, 201, response.json)
            ticket = response.json['ticket']
            ticket_id = ticket['ticket_id']
            self.assertEqual(ticket['status'], 'open')
            self.assertTrue(ticket['created_by'])
            self.assertFalse(ticket['title'].startswith(' '))
            self.assertEqual(self.client.get(f'/tickets/{ticket_id}/messages').json['messages'], [])
            response = self.client.post(f'/tickets/{ticket_id}/messages', json={'message_text':'  Test update with literal SQL: DROP TABLE tickets;  '})
            self.assertEqual(response.status_code, 201, response.json)
            message = response.json['message']
            self.assertEqual(message['ticket_id'], ticket_id)
            for status in ('in_progress', 'resolved', 'open'):
                response = self.client.patch(f'/tickets/{ticket_id}', json={'status':status})
                self.assertEqual(response.status_code, 200, response.json)
                self.assertEqual(response.json['ticket']['status'], status)
            self.engine.dispose()
            records = self.client.get('/tickets').json['tickets']
            saved = next(item for item in records if item['ticket_id']==ticket_id)
            self.assertEqual(saved['status'], 'open')
            self.assertEqual(self.client.get(f'/tickets/{ticket_id}/messages').json['messages'], [message])
            self.assertTrue(message['created_at'].endswith('+00:00'))
        finally:
            if ticket_id is not None:
                with self.engine.begin() as connection:
                    connection.execute(text('DELETE FROM support_app.ticket_messages WHERE ticket_id=:id'), {'id':ticket_id})
                    connection.execute(text('DELETE FROM support_app.tickets WHERE ticket_id=:id'), {'id':ticket_id})
        with self.engine.connect() as connection:
            after = connection.execute(text('SELECT (SELECT count(*) FROM support_app.tickets), (SELECT count(*) FROM support_app.ticket_messages)')).one()
        self.assertEqual(before, after)

    def test_frontend_assets(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Support desk', response.data)
        for path in ('/static/app.js', '/static/app.css'):
            with self.client.get(path) as asset:
                self.assertEqual(asset.status_code, 200)
        self.assertIn("script-src 'self'", response.headers['Content-Security-Policy'])
        self.assertEqual(self.client.get('/healthz').json, {'status':'ok'})

if __name__ == '__main__':
    unittest.main()
