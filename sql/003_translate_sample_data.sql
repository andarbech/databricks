-- Translate existing fictional sample records without recreating them.
BEGIN;
UPDATE support_app.tickets SET title = 'Unable to access the internal portal' WHERE title = 'No puedo acceder al portal interno';
UPDATE support_app.ticket_messages SET message_text = 'The portal has displayed a sign-in error since this morning.' WHERE message_text = 'Desde esta mañana el portal muestra un error al iniciar sesión.';
UPDATE support_app.ticket_messages SET message_text = 'We have received your report. Does this also happen in another browser?' WHERE message_text = 'Hemos recibido la incidencia. ¿Puedes confirmar si sucede en otro navegador?';
UPDATE support_app.tickets SET title = 'The sales report is taking too long' WHERE title = 'El informe de ventas tarda demasiado';
UPDATE support_app.ticket_messages SET message_text = 'The monthly report has been running for more than ten minutes.' WHERE message_text = 'El informe mensual lleva más de diez minutos ejecutándose.';
UPDATE support_app.ticket_messages SET message_text = 'We are reviewing the execution plan and date filters.' WHERE message_text = 'Estamos revisando el plan de ejecución y los filtros de fecha.';
UPDATE support_app.tickets SET title = 'Documentation access request' WHERE title = 'Solicitud de acceso a la documentación';
UPDATE support_app.ticket_messages SET message_text = 'I need permission to read the team documentation.' WHERE message_text = 'Necesito permisos para consultar la documentación del equipo.';
UPDATE support_app.ticket_messages SET message_text = 'Access has been granted and you have confirmed that it works.' WHERE message_text = 'El acceso ya está concedido y has confirmado que puedes entrar.';
UPDATE support_app.ticket_messages SET author = 'support@example.com' WHERE author = 'soporte@example.com';
COMMIT;
