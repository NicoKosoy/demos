<?php
// Registro de visitas de las demos: base de datos, ajustes y avisos por mail.
declare(strict_types=1);

date_default_timezone_set('America/Argentina/Buenos_Aires');

// Hash bcrypt de la clave del panel (la clave no está en el repo).
const CLAVE_HASH = '$2y$12$JFF7Tk5nn6aJ2gpezT1YUOXJlIa5cITQbUMms4oIvcx6RelCb4A3G';
const REMITENTE = 'avisos@resolviendokos.com';
const DEMOS = 'https://demos.resolviendokos.com/';
const PANEL = 'https://visitas.resolviendokos.com/v/';

// Los datos viven fuera de public_html: domains/<sitio>/datos
function dir_datos(): string
{
    $dir = getenv('VISITAS_DATOS') ?: dirname(__DIR__, 2) . '/datos';
    if (!is_dir($dir)) {
        mkdir($dir, 0700, true);
    }
    return $dir;
}

function db(): PDO
{
    static $pdo = null;
    if ($pdo) {
        return $pdo;
    }
    $pdo = new PDO('sqlite:' . dir_datos() . '/visitas.sqlite');
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
    $pdo->exec('PRAGMA journal_mode = WAL');
    $pdo->exec('PRAGMA busy_timeout = 3000');
    $pdo->exec('CREATE TABLE IF NOT EXISTS visitas (
        id TEXT PRIMARY KEY,
        prospecto TEXT NOT NULL,
        negocio TEXT NOT NULL DEFAULT "",
        inicio INTEGER NOT NULL,
        ultimo INTEGER NOT NULL,
        segundos INTEGER NOT NULL DEFAULT 0,
        dispositivo TEXT NOT NULL DEFAULT "",
        sistema TEXT NOT NULL DEFAULT "",
        navegador TEXT NOT NULL DEFAULT "",
        pantalla TEXT NOT NULL DEFAULT "",
        origen TEXT NOT NULL DEFAULT "",
        visitante TEXT NOT NULL DEFAULT ""
    )');
    $pdo->exec('CREATE INDEX IF NOT EXISTS visitas_prospecto ON visitas (prospecto, inicio)');
    $pdo->exec('CREATE TABLE IF NOT EXISTS avisos (
        prospecto TEXT PRIMARY KEY,
        enviado INTEGER NOT NULL,
        ok INTEGER NOT NULL
    )');
    return $pdo;
}

function ajustes(): array
{
    $f = dir_datos() . '/ajustes.json';
    return is_file($f) ? (json_decode((string) file_get_contents($f), true) ?: []) : [];
}

function guardar_ajustes(array $ajustes): void
{
    file_put_contents(dir_datos() . '/ajustes.json', json_encode($ajustes, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE), LOCK_EX);
}

// Secreto propio del servidor para firmar la cookie del panel. Se crea solo la primera vez.
function secreto(): string
{
    $f = dir_datos() . '/secreto.txt';
    if (!is_file($f)) {
        file_put_contents($f, bin2hex(random_bytes(32)), LOCK_EX);
        chmod($f, 0600);
    }
    return trim((string) file_get_contents($f));
}

function ip_cliente(): string
{
    $xff = $_SERVER['HTTP_X_FORWARDED_FOR'] ?? '';
    return $xff !== '' ? trim(explode(',', $xff)[0]) : ($_SERVER['REMOTE_ADDR'] ?? '');
}

function es_robot(string $ua): bool
{
    return $ua === '' || (bool) preg_match('/bot|crawl|spider|slurp|preview|facebookexternalhit|WhatsApp\/|HeadlessChrome|Lighthouse|python|curl|wget|Go-http/i', $ua);
}

// Devuelve [dispositivo, sistema, navegador] legibles a partir del user agent.
function leer_agente(string $ua, bool $tactil): array
{
    $sistema = match (true) {
        str_contains($ua, 'iPhone') => 'iPhone',
        str_contains($ua, 'iPad') => 'iPad',
        str_contains($ua, 'Android') => 'Android',
        str_contains($ua, 'Windows') => 'Windows',
        str_contains($ua, 'Mac OS X') => $tactil ? 'iPad' : 'Mac',
        str_contains($ua, 'CrOS') => 'Chromebook',
        str_contains($ua, 'Linux') => 'Linux',
        default => 'Otro',
    };
    $dispositivo = match (true) {
        $sistema === 'iPad', $sistema === 'Android' && !str_contains($ua, 'Mobile') => 'Tablet',
        $sistema === 'iPhone', str_contains($ua, 'Mobi') => 'Celular',
        default => 'Computadora',
    };
    $navegador = match (true) {
        str_contains($ua, 'Instagram') => 'Instagram',
        str_contains($ua, 'FBAN'), str_contains($ua, 'FBAV') => 'Facebook',
        str_contains($ua, '; wv)') => 'App (WhatsApp u otra)',
        str_contains($ua, 'Edg') => 'Edge',
        str_contains($ua, 'OPR/') => 'Opera',
        str_contains($ua, 'SamsungBrowser') => 'Samsung Internet',
        str_contains($ua, 'Firefox/'), str_contains($ua, 'FxiOS') => 'Firefox',
        str_contains($ua, 'Chrome/'), str_contains($ua, 'CriOS') => 'Chrome',
        str_contains($ua, 'Safari/') => 'Safari',
        default => 'Otro',
    };
    return [$dispositivo, $sistema, $navegador];
}

function una_linea(string $s, int $max): string
{
    $s = trim((string) preg_replace('/\s+/u', ' ', $s));
    return mb_substr($s, 0, $max);
}

function duracion(int $s): string
{
    if ($s < 60) {
        return $s . ' s';
    }
    $m = intdiv($s, 60);
    return $m < 60 ? sprintf('%d min %02d s', $m, $s % 60) : sprintf('%d h %02d min', intdiv($m, 60), $m % 60);
}

function mandar_mail(string $para, string $asunto, string $cuerpo): bool
{
    if (!filter_var($para, FILTER_VALIDATE_EMAIL)) {
        return false;
    }
    $cabeceras = implode("\r\n", [
        'From: Visitas de demos <' . REMITENTE . '>',
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=UTF-8',
        'Content-Transfer-Encoding: 8bit',
    ]);
    return mail($para, mb_encode_mimeheader(una_linea($asunto, 150), 'UTF-8', 'Q'), $cuerpo, $cabeceras, '-f' . REMITENTE);
}

function avisar_primera_visita(array $v): bool
{
    $para = ajustes()['mail'] ?? '';
    $negocio = $v['negocio'] !== '' ? $v['negocio'] : $v['prospecto'];
    $cuerpo = implode("\n", [
        "{$negocio} abrió su demo por primera vez.",
        '',
        'Cuándo: ' . date('d/m/Y H:i', $v['inicio']) . ' (hora de Argentina)',
        "Desde: {$v['dispositivo']} · {$v['sistema']} · {$v['navegador']}",
        'Demo: ' . DEMOS . $v['prospecto'] . '/?yo=1',
        '',
        'Cuánto se queda y si vuelve a entrar lo ves en el panel:',
        PANEL,
    ]);
    return mandar_mail($para, "{$negocio} abrió su demo", $cuerpo);
}
