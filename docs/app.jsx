// TRENT — App principal con edición inline

const { useState, useEffect, useRef, useMemo } = React;

const DEFAULTS = {
  primaryColor: "#1E3FBE",
  bgMode: "warm",
  density: "regular",
  displayFont: "Archivo Black",
  heroCopy: "Prendas seleccionadas cada día. Descarga la app, entra al Telegram, encuentra tu estilo, aplica TRENT14 y compra.",
  discountCode: "TRENT14",
  discountPct: "14",
  metric1Num: "+340", metric1Lbl: "Prendas activas",
  metric2Num: "−14%", metric2Lbl: "1ª compra · TRENT14",
  metric3Num: "7–15",  metric3Lbl: "Entrega media",
  marquee1: "NUEVOS LINKS CADA DÍA",
  marquee2: "ENVÍO 7–15 DÍAS",
  marquee3: "SUB 20€ MAYORÍA",
  marquee4: "SOPORTE 1 A 1 EN TELEGRAM",
  marquee5: "SIN PASARELAS RAROS",
  marquee6: "GUÍAS DE TALLAS",
  telegramLink: "https://t.me/trentthacoo",
  telegramMembers: "12.4k miembros · activos hoy",
};

const BG_THEMES = {
  warm:  { bg: '#ECECEC', bgSoft: '#F5F4F0', surface: '#FFFFFF', ink: '#0A0A12', mute: '#5E5E68', border: '#D6D5D0' },
  cool:  { bg: '#E8EBF1', bgSoft: '#F1F3F8', surface: '#FFFFFF', ink: '#0A0A14', mute: '#5A5F70', border: '#D2D6E0' },
  paper: { bg: '#F4EDE1', bgSoft: '#FBF6EC', surface: '#FFFFFF', ink: '#1A1408', mute: '#6B5E48', border: '#E0D4BF' },
  dark:  { bg: '#0E0E14', bgSoft: '#16161E', surface: '#1C1C26', ink: '#F2F2F2', mute: '#9A9AA8', border: '#2A2A36' },
};

const FONT_STACKS = {
  'Archivo Black': "'Archivo Black', 'Helvetica Neue', Arial, sans-serif",
  'Bowlby One':    "'Bowlby One', 'Archivo Black', sans-serif",
  'Anton':         "'Anton', 'Archivo Black', sans-serif",
  'Space Grotesk': "'Space Grotesk', 'Inter Tight', system-ui, sans-serif",
};

// ── EditableText ──────────────────────────────────────────────
// Renderiza texto normal o contenteditable según editMode
function EditableText({ value, fieldKey, editMode, onSave, tag = 'span', className, style, children }) {
  const ref = useRef(null);

  useEffect(() => {
    if (ref.current && editMode) ref.current.textContent = value;
  }, [value, editMode]);

  if (!editMode) {
    const Tag = tag;
    return <Tag className={className} style={style}>{children || value}</Tag>;
  }

  const Tag = tag;
  return (
    <Tag
      ref={ref}
      className={className}
      style={{
        ...style,
        outline: '2px dashed #1E3FBE',
        outlineOffset: 3,
        borderRadius: 4,
        cursor: 'text',
        minWidth: 20,
        display: 'inline-block',
      }}
      contentEditable
      suppressContentEditableWarning
      onBlur={(e) => onSave(fieldKey, e.currentTarget.textContent.trim())}
      title="Haz clic para editar"
    />
  );
}
window.EditableText = EditableText;

// ── App ───────────────────────────────────────────────────────
function App() {
  const [cfg, setCfg] = useState(DEFAULTS);
  const [editMode, setEditMode] = useState(false);
  const [showPwd, setShowPwd] = useState(false);
  const [pwd, setPwd] = useState('');
  const [pwdErr, setPwdErr] = useState('');
  const [savedKey, setSavedKey] = useState(null);

  // Cargar config de Firestore
  useEffect(() => {
    if (!window._db) return;
    const unsub = window._db.collection('config').doc('site').onSnapshot(snap => {
      if (snap.exists()) setCfg(c => ({ ...c, ...snap.data() }));
    });
    return () => unsub();
  }, []);

  // CSS vars
  const theme = BG_THEMES[cfg.bgMode] || BG_THEMES.warm;
  const palette = { primary: cfg.primaryColor, ...theme };

  useEffect(() => {
    const r = document.documentElement;
    r.style.setProperty('--c-primary', cfg.primaryColor);
    r.style.setProperty('--c-bg', theme.bg);
    r.style.setProperty('--c-bg-soft', theme.bgSoft);
    r.style.setProperty('--c-surface', theme.surface);
    r.style.setProperty('--c-ink', theme.ink);
    r.style.setProperty('--c-mute', theme.mute);
    r.style.setProperty('--c-border', theme.border);
    r.style.setProperty('--font-display', FONT_STACKS[cfg.displayFont] || FONT_STACKS['Archivo Black']);
    r.dataset.bgMode = cfg.bgMode;
  }, [cfg.primaryColor, cfg.bgMode, cfg.displayFont]);

  // Guardar campo en Firestore
  const saveField = async (key, value) => {
    setCfg(c => ({ ...c, [key]: value }));
    if (!window._db) return;
    try {
      await window._db.collection('config').doc('site').set({ [key]: value }, { merge: true });
      setSavedKey(key);
      setTimeout(() => setSavedKey(null), 1500);
    } catch(e) { console.error('saveField error', e); }
  };

  // Login edit mode
  const tryLogin = async () => {
    setPwdErr('');
    if (!pwd) { setPwdErr('Escribe la contraseña'); return; }
    const DEFAULT_PWD = 'trent2026';
    try {
      const doc = await window._db.collection('config').doc('admin').get();
      const stored = (doc.exists() && doc.data().password) ? doc.data().password : DEFAULT_PWD;
      if (pwd === stored) { setEditMode(true); setShowPwd(false); setPwd(''); }
      else setPwdErr('Contraseña incorrecta');
    } catch {
      if (pwd === DEFAULT_PWD) { setEditMode(true); setShowPwd(false); setPwd(''); }
      else setPwdErr('Error de conexión');
    }
  };

  const scrollTo = (id) => {
    const el = id === 'top' ? document.body : document.getElementById(id);
    if (!el) return;
    if (id === 'top') window.scrollTo({ top: 0, behavior: 'smooth' });
    else window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 60, behavior: 'smooth' });
  };

  const marqueeItems = [cfg.marquee1, cfg.marquee2, cfg.marquee3, cfg.marquee4, cfg.marquee5, cfg.marquee6];

  return (
    <div className="page">
      <Navbar onScrollTo={scrollTo} />
      <Hero cfg={cfg} onScrollTo={scrollTo} palette={palette} editMode={editMode} onSave={saveField} />
      <Marquee items={marqueeItems} />
      <HowToBuy />
      <Catalog density={cfg.density} palette={palette} />
      <TelegramBlock cfg={cfg} editMode={editMode} onSave={saveField} />
      <Guides />
      <FAQ />
      <Footer />

      {/* Botón flotante editar */}
      {!editMode && (
        <button
          onClick={() => setShowPwd(true)}
          style={{
            position: 'fixed', bottom: 24, right: 24, zIndex: 9999,
            background: '#1E3FBE', color: '#fff', border: 'none',
            borderRadius: 50, padding: '12px 20px', fontFamily: 'inherit',
            fontSize: 14, fontWeight: 600, cursor: 'pointer',
            boxShadow: '0 4px 20px rgba(30,63,190,.4)',
            display: 'flex', alignItems: 'center', gap: 8,
          }}
        >
          ✏️ Editar web
        </button>
      )}

      {editMode && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 9999,
          background: '#1E3FBE', color: '#fff',
          borderRadius: 12, padding: '10px 18px',
          fontFamily: 'inherit', fontSize: 13, fontWeight: 600,
          boxShadow: '0 4px 20px rgba(30,63,190,.4)',
          display: 'flex', alignItems: 'center', gap: 12,
        }}>
          {savedKey ? '✅ Guardado' : '✏️ Modo edición — haz clic en cualquier texto'}
          <button onClick={() => setEditMode(false)} style={{
            background: 'rgba(255,255,255,.2)', border: 'none', color: '#fff',
            borderRadius: 8, padding: '4px 10px', fontFamily: 'inherit',
            fontSize: 12, cursor: 'pointer',
          }}>Salir</button>
        </div>
      )}

      {/* Modal contraseña */}
      {showPwd && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)',
          zIndex: 99999, display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} onClick={() => setShowPwd(false)}>
          <div style={{
            background: '#fff', borderRadius: 16, padding: 32, width: 320,
            boxShadow: '0 20px 60px rgba(0,0,0,.2)',
          }} onClick={e => e.stopPropagation()}>
            <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 16 }}>Acceso editor</div>
            <input
              type="password"
              placeholder="Contraseña"
              value={pwd}
              onChange={e => setPwd(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && tryLogin()}
              autoFocus
              style={{
                width: '100%', padding: '10px 12px', borderRadius: 8,
                border: '1.5px solid #D6D5D0', fontFamily: 'inherit',
                fontSize: 14, outline: 'none', marginBottom: 8, boxSizing: 'border-box',
              }}
            />
            {pwdErr && <div style={{ color: '#E63A2E', fontSize: 13, marginBottom: 8 }}>{pwdErr}</div>}
            <button onClick={tryLogin} style={{
              width: '100%', padding: '11px', background: '#1E3FBE', color: '#fff',
              border: 'none', borderRadius: 8, fontFamily: 'inherit',
              fontSize: 14, fontWeight: 600, cursor: 'pointer',
            }}>Entrar</button>
          </div>
        </div>
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
