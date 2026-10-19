<?php
// Panel privado: quién abrió su demo, cuándo, desde qué dispositivo y cuánto se quedó.
declare(strict_types=1);
require __DIR__ . '/lib.php';

header('Cache-Control: no-store, private');
header('X-Robots-Tag: noindex, nofollow');
header('X-Frame-Options: DENY');

const COOKIE = 'rk_panel';
const DIAS_SESION = 180;

function firma(string $s): string
{
    return hash_hmac('sha256', $s, secreto());
}

function sesion_valida(): bool
{
    $c = $_COOKIE[COOKIE] ?? '';
    [$vence, $f] = array_pad(explode('.', $c, 2), 2, '');
    return ctype_digit($vence) && (int) $vence > time() && hash_equals(firma($vence), $f);
}

function e(string $s): string
{
    return htmlspecialchars($s, ENT_QUOTES, 'UTF-8');
}

function cuando(int $t): string
{
    $dia = date('Y-m-d', $t);
    if ($dia === date('Y-m-d')) {
        return 'hoy ' . date('H:i', $t);
    }
    if ($dia === date('Y-m-d', strtotime('-1 day'))) {
        return 'ayer ' . date('H:i', $t);
    }
    return date('d/m H:i', $t);
}

$mensaje = '';
$ok_sesion = sesion_valida();

if (isset($_GET['salir'])) {
    setcookie(COOKIE, '', ['expires' => 1, 'path' => '/v/', 'secure' => true, 'httponly' => true, 'samesite' => 'Lax']);
    header('Location: ./');
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['clave'])) {
    if (password_verify((string) $_POST['clave'], CLAVE_HASH)) {
        $vence = (string) (time() + DIAS_SESION * 86400);
        setcookie(COOKIE, $vence . '.' . firma($vence), ['expires' => (int) $vence, 'path' => '/v/', 'secure' => true, 'httponly' => true, 'samesite' => 'Lax']);
        header('Location: ./');
        exit;
    }
    sleep(2);
    $mensaje = 'Clave incorrecta.';
}

if ($ok_sesion && $_SERVER['REQUEST_METHOD'] === 'POST' && hash_equals(firma('csrf' . ($_COOKIE[COOKIE] ?? '')), (string) ($_POST['csrf'] ?? ''))) {
    $ajustes = ajustes();
    if (isset($_POST['mail'])) {
        $mail = trim((string) $_POST['mail']);
        if ($mail === '' || filter_var($mail, FILTER_VALIDATE_EMAIL)) {
            $ajustes['mail'] = $mail;
            guardar_ajustes($ajustes);
            $mensaje = $mail === '' ? 'Avisos por mail desactivados.' : 'Listo: los avisos van a llegar a ' . $mail . '.';
        } else {
            $mensaje = 'Ese mail no parece válido.';
        }
    }
    if (isset($_POST['probar'])) {
        $ok = mandar_mail($ajustes['mail'] ?? '', 'Prueba del panel de visitas', "Si te llegó este mail, los avisos de primera visita funcionan.\n\nPanel: " . PANEL);
        $mensaje = $ok ? 'Mail de prueba enviado. Si no lo ves en unos minutos, buscalo en Spam y marcalo como "No es spam".' : 'No se pudo enviar. Revisá el mail cargado.';
    }
}

$css = <<<'CSS'
:root{--bg:#F4F2EE;--card:#FFFFFF;--line:#E2DED6;--fg:#1D1B18;--fg2:#6B655C;--acc:#0F6E56;--acc2:#E4F1EC;--warn:#9A5B00;--warnbg:#FBF0DD}
@media (prefers-color-scheme:dark){:root{--bg:#141311;--card:#1D1C19;--line:#34312C;--fg:#EEEAE3;--fg2:#A39C91;--acc:#5CC6A2;--acc2:#1B2E27;--warn:#E8B04F;--warnbg:#33281A}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:24px 16px 60px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:17px;margin:0 0 12px}
.sub{color:var(--fg2);margin:0}
.top{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap;margin-bottom:20px}
a{color:var(--acc)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin-bottom:18px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:18px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi b{display:block;font-size:28px;line-height:1.1;font-variant-numeric:tabular-nums}.kpi span{color:var(--fg2);font-size:13px}
.tw{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;color:var(--fg2);font-weight:600;font-size:12.5px;padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}tr:last-child td{border-bottom:0}
.num{font-variant-numeric:tabular-nums;white-space:nowrap}.muted{color:var(--fg2);font-size:13px}
.pill{display:inline-block;background:var(--acc2);color:var(--acc);border-radius:999px;padding:1px 9px;font-size:12.5px;font-weight:600}
.msg{background:var(--acc2);color:var(--acc);border-radius:10px;padding:10px 14px;margin-bottom:18px}
.warn{background:var(--warnbg);color:var(--warn)}
form.inline{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
input[type=email],input[type=password]{font:inherit;padding:9px 11px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg);min-width:0;flex:1 1 240px}
button{font:inherit;font-weight:600;padding:9px 14px;border-radius:8px;border:1px solid var(--acc);background:var(--acc);color:#fff;cursor:pointer}
button.sec{background:transparent;color:var(--acc)}
.login{max-width:380px;margin:12vh auto 0}
CSS;

if (!$ok_sesion) {
    ?><!doctype html><html lang="es-AR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Visitas a las demos</title><style><?= $css ?></style></head>
<body><div class="wrap"><div class="card login">
<h1>Visitas a las demos</h1><p class="sub" style="margin-bottom:16px">Entrá con tu clave.</p>
<?php if ($mensaje): ?><div class="msg warn"><?= e($mensaje) ?></div><?php endif; ?>
<form method="post" class="inline"><input type="password" name="clave" autocomplete="current-password" placeholder="Clave" required autofocus><button>Entrar</button></form>
</div></div></body></html><?php
    exit;
}

$pdo = db();
$ajustes = ajustes();
$csrf = firma('csrf' . ($_COOKIE[COOKIE] ?? ''));
$filtro = preg_match('/^[a-z0-9-]{3,80}$/', (string) ($_GET['p'] ?? '')) ? (string) $_GET['p'] : '';

$k = $pdo->query('SELECT COUNT(DISTINCT prospecto) AS prospectos, COUNT(*) AS visitas,
    COALESCE(AVG(segundos), 0) AS promedio,
    SUM(CASE WHEN inicio >= ' . strtotime('-7 days') . ' THEN 1 ELSE 0 END) AS semana FROM visitas WHERE prospecto NOT LIKE \'prueba-%\'')->fetch();

$por_prospecto = $pdo->query('SELECT prospecto, MAX(negocio) AS negocio, MIN(inicio) AS primera, MAX(inicio) AS ultima,
    COUNT(*) AS visitas, SUM(segundos) AS total, COUNT(DISTINCT visitante) AS personas,
    GROUP_CONCAT(DISTINCT dispositivo) AS dispositivos
    FROM visitas WHERE prospecto NOT LIKE \'prueba-%\' GROUP BY prospecto ORDER BY ultima DESC')->fetchAll();

$q = $pdo->prepare('SELECT * FROM visitas WHERE ' . ($filtro ? 'prospecto = ? ' : "prospecto NOT LIKE 'prueba-%' ") . 'ORDER BY inicio DESC LIMIT 300');
$q->execute($filtro ? [$filtro] : []);
$ultimas = $q->fetchAll();
?><!doctype html><html lang="es-AR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Visitas a las demos</title><style><?= $css ?></style></head>
<body><div class="wrap">
<div class="top"><div><h1>Visitas a las demos</h1><p class="sub">Solo cuenta prospectos: tus visitas con <b>?yo=1</b> no se registran. Hora de Argentina.</p></div><a href="?salir">Salir</a></div>
<?php if ($mensaje): ?><div class="msg"><?= e($mensaje) ?></div><?php endif; ?>
<?php if (empty($ajustes['mail'])): ?><div class="msg warn">Falta cargar a qué mail te aviso cuando un prospecto abre su demo por primera vez. Está abajo de todo.</div><?php endif; ?>

<div class="kpis">
  <div class="kpi"><b><?= (int) $k['prospectos'] ?></b><span>prospectos abrieron su demo</span></div>
  <div class="kpi"><b><?= (int) $k['visitas'] ?></b><span>visitas en total</span></div>
  <div class="kpi"><b><?= (int) $k['semana'] ?></b><span>visitas en los últimos 7 días</span></div>
  <div class="kpi"><b><?= e(duracion((int) round((float) $k['promedio']))) ?></b><span>tiempo promedio por visita</span></div>
</div>

<div class="card"><h2>Por prospecto</h2>
<?php if (!$por_prospecto): ?><p class="muted">Todavía nadie abrió su demo. Cuando pase, aparece acá y te llega un mail.</p>
<?php else: ?><div class="tw"><table><thead><tr><th>Negocio</th><th>Primera vez</th><th>Última</th><th>Visitas</th><th>Tiempo total</th><th>Desde</th></tr></thead><tbody>
<?php foreach ($por_prospecto as $p): ?>
<tr><td><a href="?p=<?= e($p['prospecto']) ?>"><?= e($p['negocio'] ?: $p['prospecto']) ?></a><div class="muted"><a href="<?= e(DEMOS . $p['prospecto'] . '/?yo=1') ?>" target="_blank" rel="noopener">ver demo</a><?= (int) $p['personas'] > 1 ? ' · ' . (int) $p['personas'] . ' personas distintas' : '' ?></div></td>
<td class="num"><?= e(cuando((int) $p['primera'])) ?></td><td class="num"><?= e(cuando((int) $p['ultima'])) ?></td>
<td class="num"><?= (int) $p['visitas'] ?></td><td class="num"><?= e(duracion((int) $p['total'])) ?></td><td><?= e(str_replace(',', ', ', (string) $p['dispositivos'])) ?></td></tr>
<?php endforeach; ?></tbody></table></div><?php endif; ?>
</div>

<div class="card"><h2><?= $filtro ? 'Visitas de ' . e($ultimas[0]['negocio'] ?? $filtro) . ' · <a href="./" style="font-size:14px;font-weight:500">ver todas</a>' : 'Últimas visitas' ?></h2>
<?php if (!$ultimas): ?><p class="muted">Sin visitas todavía.</p>
<?php else: ?><div class="tw"><table><thead><tr><th>Cuándo</th><th>Negocio</th><th>Dispositivo</th><th>Tiempo</th><th>Llegó desde</th></tr></thead><tbody>
<?php foreach ($ultimas as $v): $origen = $v['origen'] ? (parse_url($v['origen'], PHP_URL_HOST) ?: $v['origen']) : 'link directo'; ?>
<tr><td class="num"><?= e(cuando((int) $v['inicio'])) ?></td><td><?= e($v['negocio'] ?: $v['prospecto']) ?></td>
<td><?= e($v['dispositivo']) ?> <span class="muted">· <?= e($v['sistema']) ?> · <?= e($v['navegador']) ?></span></td>
<td class="num"><?= e(duracion((int) $v['segundos'])) ?></td><td class="muted"><?= e($origen) ?></td></tr>
<?php endforeach; ?></tbody></table></div><?php endif; ?>
</div>

<div class="card"><h2>Aviso por mail</h2>
<p class="muted" style="margin-top:0">Te mando un mail la primera vez que cada prospecto abre su demo.</p>
<form method="post" class="inline"><input type="hidden" name="csrf" value="<?= e($csrf) ?>"><input type="email" name="mail" value="<?= e((string) ($ajustes['mail'] ?? '')) ?>" placeholder="tu@mail.com"><button>Guardar</button></form>
<?php if (!empty($ajustes['mail'])): ?><form method="post" style="margin-top:10px"><input type="hidden" name="csrf" value="<?= e($csrf) ?>"><button class="sec" name="probar" value="1">Mandarme un mail de prueba</button></form><?php endif; ?>
</div>
</div></body></html>
