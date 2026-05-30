// TRENT — App principal con editor inline completo

const { useState, useEffect, useRef, useMemo, createContext, useContext } = React;

// ── Context compartido por todos los componentes ──────────────
const EditCtx = createContext({ editMode: false, cfg: {}, onSave: () => {} });
window.EditCtx = EditCtx;

// ── Valores por defecto (también definen los keys de Firestore) ──
const DEFAULTS = {
  primaryColor: "#1E3FBE", bgMode: "warm", density: "regular", displayFont: "Archivo Black",

  // Barra superior
  discountCode: "TRENT14", discountPct: "14", shippingText: "envío 7–15 días",

  // Hero
  heroEyebrow: "Drops nuevos cada día · Código bienvenida −14%",
  heroCopy: "Prendas seleccionadas cada día. Descarga la app, entra al Telegram, encuentra tu estilo, aplica TRENT14 y compra.",
  metric1Num: "+340", metric1Lbl: "Prendas activas",
  metric2Num: "−14%", metric2Lbl: "1ª compra · TRENT14",
  metric3Num: "7–15",  metric3Lbl: "Entrega media",
  heroBtnPrimary: "Ver catálogo en Telegram",
  heroBtnSecondary: "Cómo funciona",
  heroCardName: "Hoodie Boxy Cream", heroCardCat: "Sudaderas · TRENT", heroCardPrice: "12,40€",

  // Marquee
  marquee1: "NUEVOS LINKS CADA DÍA", marquee2: "ENVÍO 7–15 DÍAS",
  marquee3: "SUB 20€ MAYORÍA",        marquee4: "SOPORTE 1 A 1 EN TELEGRAM",
  marquee5: "SIN PASARELAS RAROS",    marquee6: "GUÍAS DE TALLAS",

  // Cómo comprar
  howTitle: "Cómprate todo en 4 pasos.",
  howLead: "Pulsa cada paso y te lleva directo. Si es tu primera vez, tarda un café. Después, 30 segundos.",
  step0title: "Descarga la app",      step0body: "Disponible en iOS y Android. Es donde compras todas tus prendas TRENT.",      step0tag: "iOS · Android",
  step1title: "Únete a mi Telegram",  step1body: "El canal donde publico cada día los enlaces a las mejores prendas seleccionadas.", step1tag: "+12k miembros",
  step2title: "Encuentra tu prenda",  step2body: "Busca en nuestro catálogo o en el canal. Filtra por marca, categoría y precio.",  step2tag: "Búsqueda rápida",
  step3title: "Aplica el código",     step3body: "En el checkout escribe TRENT14 y te descuenta un 14% en tu primera compra.",       step3tag: "−14% 1ª compra",

  // Telegram block
  telegramTitle: "Mi Telegram es donde vive todo.",
  telegramLead: "Es el canal donde publico cada día los enlaces directos a las prendas. De la inspiración a tu carrito en 1 toque.",
  telegramLink: "https://t.me/trentthacoo", telegramMembers: "12.4k miembros · activos hoy",
  benefit0t: "Links organizados por categoría", benefit0s: "Sneakers, hoodies, cargos… cada uno con su carpeta. Sin scroll infinito.",
  benefit1t: "Drops en directo",               benefit1s: "Cuando encuentro algo bueno, te llega al móvil. Lo pillas antes que nadie.",
  benefit2t: "Soporte 1 a 1",                  benefit2s: "¿Dudas de talla o incidencia? Me escribes y te ayudo personalmente.",
  benefit3t: "Gratis y sin spam",              benefit3s: "Solo subo cuando vale la pena. Cero publi de relleno.",

  // FAQ
  faq0q: "¿Cuánto tarda el envío?",            faq0a: "Entre 7 y 15 días hábiles según el destino. La mayoría llega en 10 días.",
  faq1q: "¿Pago aduanas?",                     faq1a: "En pedidos bajo 150€ suele entrar sin problemas. Por encima puede haber tasas según aduana.",
  faq2q: "¿Qué pasa si me llega mal?",         faq2a: "Abre una disputa en la app en 72h. Hacoo suele reembolsar o reenviar sin coste.",
  faq3q: "¿Es fiable Hacoo?",                  faq3a: "Sí. Es una plataforma con años de historia. Yo mismo compro ahí y selecciono solo lo que he probado o verificado.",
  faq4q: "¿Necesito cuenta para comprar?",     faq4a: "Sí, crea una cuenta gratuita en la app. Solo tarda 1 minuto con el email.",

  // Footer
  footerCta1: "¿Listo para", footerCta2: "PILLAR DROPS?",
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
function EditableText({ value, fieldKey, tag = 'span', className, style }) {
  const { editMode, onSave } = useContext(EditCtx);
  const ref = useRef(null);

  useEffect(() => {
    if (ref.current && editMode) ref.current.textContent = value;
  }, [value, editMode]);

  const Tag = tag;
  if (!editMode) return <Tag className={className} style={style}>{value}</Tag>;

  return (
    <Tag
      ref={ref}
      className={className}
      style={{ ...style, outline: '2px dashed #1E3FBE', outlineOffset: 3, borderRadius: 4, cursor: 'text', minWidth: 20, display: 'inline-block' }}
      contentEditable suppressContentEditableWarning
      onBlur={e => onSave(fieldKey, e.currentTarget.textContent.trim())}
      title="Haz clic para editar"
    />
  );
}
window.EditableText = EditableText;

// ── App ───────────────────────────────────────────────────────
function App() {
  const [cfg, setCfg] = useState(DEFAULTS);
  const inEditFrame = new URLSearchParams(location.search).get('edit') === '1';
  const [editMode, setEditMode] = useState(inEditFrame);
  const [savedKey, setSavedKey] = useState(null);

  useEffect(() => {
    if (!window._db) return;
    const unsub = window._db.collection('config').doc('site').onSnapshot(snap => {
      if (snap.exists()) setCfg(c => ({ ...c, ...snap.data() }));
    });
    return () => unsub();
  }, []);

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

  const onSave = async (key, value) => {
    setCfg(c => ({ ...c, [key]: value }));
    if (!window._db) return;
    try {
      await window._db.collection('config').doc('site').set({ [key]: value }, { merge: true });
      setSavedKey(key);
      setTimeout(() => setSavedKey(null), 1500);
    } catch(e) { console.error('save error', e); }
  };

  const scrollTo = (id) => {
    const el = id === 'top' ? document.body : document.getElementById(id);
    if (!el) return;
    if (id === 'top') window.scrollTo({ top: 0, behavior: 'smooth' });
    else window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 60, behavior: 'smooth' });
  };

  const marqueeItems = [cfg.marquee1, cfg.marquee2, cfg.marquee3, cfg.marquee4, cfg.marquee5, cfg.marquee6];

  return (
    <EditCtx.Provider value={{ editMode, cfg, onSave }}>
      <div className="page">
        <Navbar onScrollTo={scrollTo} />
        <Hero onScrollTo={scrollTo} palette={palette} />
        <Marquee items={marqueeItems} />
        <HowToBuy />
        <Catalog density={cfg.density} palette={palette} />
        <TelegramBlock />
        <Guides />
        <FAQ />
        <Footer />

        {editMode && (
          <div style={{
            position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 9999,
            background: '#1E3FBE', color: '#fff',
            padding: '10px 20px', fontFamily: 'inherit', fontSize: 13, fontWeight: 600,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16,
          }}>
            {savedKey ? '✅ Guardado' : '✏️ Modo edición activo — haz clic en cualquier texto con borde azul para editarlo'}
          </div>
        )}
      </div>
    </EditCtx.Provider>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
