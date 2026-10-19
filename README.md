# Registro de visitas de las demos

Se publica en Hostinger en https://visitas.resolviendokos.com/v/ (deploy por Git de esta rama).

- `t.js`: script que carga cada demo. Manda "inicio" al abrir y "ping" con los segundos que lleva visible.
- `c.php`: recibe esos avisos y los guarda en SQLite, fuera de public_html (`domains/visitas.resolviendokos.com/datos`). La primera visita de cada prospecto dispara un mail.
- `index.php`: panel privado con clave. Ahí se carga el mail para los avisos.
- `?yo=1` en cualquier demo marca ese navegador como propio y no cuenta sus visitas.
