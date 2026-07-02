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
  heroEyebrow: "Prendas nuevas cada día · Código bienvenida −14%",
  heroCopy: "Descarga la app, entra al chat de Telegram, encuentra tus marcas favoritas, aplica el código de descuento TRENT14 y compra.",
  metric1Num: "+340", metric1Lbl: "Prendas",
  metric2Num: "−14%", metric2Lbl: "Código: TRENT14",
  metric3Num: "7–15",  metric3Lbl: "Días de entrega",
  heroBtnPrimary: "Únete a Telegram",
  heroBtnSecondary: "Todos los links",
  heroCardName: "Nude Project Resort Tee", heroCardCat: "Camisetas · Nude Project", heroCardPrice: "11,00€",
  heroCardImages: ["https://i.ibb.co/N6dBVffc/5834782908244234434.jpg", "https://i.ibb.co/ZzBCgqm5/5834782908244234435.jpg"],
  heroCardLink: "",

  // Marquee
  marquee1: "NUEVOS LINKS CADA DÍA", marquee2: "ENVÍO 7–15 DÍAS",
  marquee3: "SUB 20€ MAYORÍA",        marquee4: "SOPORTE 1 A 1 EN TELEGRAM",
  marquee5: "SIN PASARELAS RAROS",    marquee6: "GUÍAS DE TALLAS",

  // Cómo comprar
  howTitle: "Compra en 4 pasos.",
  howLead: "¿Es tu primera compra? Sigue los pasos, solo serán 30 segundos.",
  step0title: "Descarga la app",      step0body: "Disponible en iOS y Android. Clica el botón y descarga la app en tu móvil.",      step0tag: "Descarga HACOO",
  step1title: "Únete a mi Telegram",  step1body: "El canal donde publico cada día los enlaces verificados a todas las prendas.", step1tag: "Chat Telegram",
  step2title: "Encuentra tu prenda",  step2body: "Busca en nuestro catálogo o en el canal. Filtra por marca, categoría y precio.",  step2tag: "Búsqueda rápida",
  step3title: "Aplica el código",     step3body: "En el checkout escribe TRENT14 y aplica el descuento del 14%.",       step3tag: "Código: TRENT14",

  // Telegram block
  telegramTitle: "Descubre todas las novedades en Telegram",
  telegramLead: "Únete al canal donde publico cada día nuevos enlaces a las prendas.",
  telegramLink: "https://t.me/trentthacoo", telegramMembers: "12.4k miembros activos",
  benefit0t: "Links organizados por categoría", benefit0s: "Escribe lo que quieres en el buscador del chat y clica.",
  benefit1t: "Actualizaciones cada día",       benefit1s: "Con nuevos enlaces verificados cada día.",
  benefit2t: "Soporte 1 a 1",                  benefit2s: "¿Dudas de talla o incidencias? Me escribes y te ayudo.",
  benefit3t: "Gratis y sin spam",              benefit3s: "Solo subo cuando vale la pena. Cero publi de relleno.",

  // FAQ
  faq0q: "¿Cuánto tarda el envío?",            faq0a: "Entre 7 y 15 días hábiles según el destino. La mayoría llega en 10 días.",
  faq1q: "¿Pago aduanas?",                     faq1a: "No. Hacoo usa el sistema IOSS, por lo que el IVA ya está incluido en el precio que ves. En compras bajo 150€ no pagas nada extra al recibir el paquete. Si por algún motivo te cobran algo en aduana, Hacoo lo reembolsa — guarda la factura y contacta con su soporte.",
  faq2q: "¿Qué pasa si me llega mal?",         faq2a: "Abre una disputa en la app en 72h. Hacoo suele reembolsar o reenviar sin coste.",
  faq3q: "¿Es fiable Hacoo?",                  faq3a: "Sí. Es una plataforma con años de historia. Yo mismo compro ahí y selecciono solo lo que he probado o verificado.",
  faq4q: "¿Necesito cuenta para comprar?",     faq4a: "Sí, crea una cuenta gratuita en la app — solo tarda 1 minuto con tu email. Al registrarte y hacer tu primera compra, usa el código TRENT14 para llevarte un 14% de descuento. ¡No te lo pierdas!",

  // Footer
  footerCta1: "¿Listo para", footerCta2: "tu nuevo pedido?",
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
      if (snap.exists) setCfg(c => ({ ...c, ...snap.data() }));
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
        <Catalog density={cfg.density} palette={palette} />
        <HowToBuy />
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
