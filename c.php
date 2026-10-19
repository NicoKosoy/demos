<?php
// Recibe los avisos que manda t.js desde cada demo: "inicio" al abrir y "ping" con los segundos que lleva.
declare(strict_types=1);
require __DIR__ . '/lib.php';

header('Access-Control-Allow-Origin: *');
header('Cache-Control: no-store');

if (isset($_GET['estado'])) {
    // Chequeo público del servidor, sin datos de visitas.
    header('Content-Type: application/json');
    $ok_datos = is_writable(dir_datos());
    echo json_encode([
        'php' => PHP_VERSION,
        'sqlite' => extension_loaded('pdo_sqlite'),
        'mail' => function_exists('mail'),
        'datos_escribibles' => $ok_datos,
        'base' => $ok_datos && (bool) db(),
    ]);
    exit;
}

$entrada = json_decode((string) file_get_contents('php://input'), true);
$d = is_array($entrada) ? $entrada : $_GET;

$evento = $d['e'] ?? '';
$id = (string) ($d['v'] ?? '');
$ua = $_SERVER['HTTP_USER_AGENT'] ?? '';
if (!preg_match('/^[a-z0-9]{8,32}$/', $id) || es_robot($ua) || !empty($d['yo'])) {
    http_response_code(204);
    exit;
}

$ahora = time();
$pdo = db();

if ($evento === 'inicio') {
    $prospecto = (string) ($d['p'] ?? '');
    if (!preg_match('/^[a-z0-9][a-z0-9-]{2,80}$/', $prospecto)) {
        http_response_code(204);
        exit;
    }
    [$dispositivo, $sistema, $navegador] = leer_agente($ua, !empty($d['t']));
    $v = [
        'id' => $id,
        'prospecto' => $prospecto,
        'negocio' => una_linea((string) ($d['n'] ?? ''), 120),
        'inicio' => $ahora,
        'ultimo' => $ahora,
        'dispositivo' => $dispositivo,
        'sistema' => $sistema,
        'navegador' => $navegador,
        'pantalla' => una_linea((string) ($d['w'] ?? ''), 20),
        'origen' => una_linea((string) ($d['r'] ?? ''), 200),
        'visitante' => substr(hash('sha256', ip_cliente() . '|' . $ua . '|' . secreto()), 0, 12),
    ];
    $pdo->prepare('INSERT OR IGNORE INTO visitas (id, prospecto, negocio, inicio, ultimo, dispositivo, sistema, navegador, pantalla, origen, visitante)
        VALUES (:id, :prospecto, :negocio, :inicio, :ultimo, :dispositivo, :sistema, :navegador, :pantalla, :origen, :visitante)')->execute($v);

    // Primera vez que este prospecto abre su demo: un solo aviso por prospecto.
    $nuevo = $pdo->prepare('INSERT OR IGNORE INTO avisos (prospecto, enviado, ok) VALUES (?, ?, 0)');
    $nuevo->execute([$prospecto, $ahora]);
    http_response_code(204);
    if ($nuevo->rowCount() === 1) {
        if (function_exists('litespeed_finish_request')) {
            litespeed_finish_request();
        } elseif (function_exists('fastcgi_finish_request')) {
            fastcgi_finish_request();
        }
        $ok = avisar_primera_visita($v);
        $pdo->prepare('UPDATE avisos SET ok = ? WHERE prospecto = ?')->execute([$ok ? 1 : 0, $prospecto]);
    }
    exit;
}

if ($evento === 'ping') {
    // Tiempo con la pestaña visible; tope de 4 horas por visita.
    $segundos = max(0, min(14400, (int) ($d['s'] ?? 0)));
    $pdo->prepare('UPDATE visitas SET segundos = MAX(segundos, ?), ultimo = ? WHERE id = ? AND inicio > ?')
        ->execute([$segundos, $ahora, $id, $ahora - 86400]);
}
http_response_code(204);
