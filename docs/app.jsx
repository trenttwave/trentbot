// TRENT — App principal con Tweaks

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "primaryColor": "#1E3FBE",
  "bgMode": "warm",
  "density": "regular",
  "displayFont": "Archivo Black",
  "heroCopy": "Prendas seleccionadas cada día. Descarga la app, entra al Telegram, encuentra tu estilo, aplica TRENT14 y compra."
}/*EDITMODE-END*/;

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

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);

  const theme = BG_THEMES[t.bgMode] || BG_THEMES.warm;
  const palette = { primary: t.primaryColor, ...theme };

  // expose CSS variables for the page
  useEffect(() => {
    const r = document.documentElement;
    r.style.setProperty('--c-primary', t.primaryColor);
    r.style.setProperty('--c-bg', theme.bg);
    r.style.setProperty('--c-bg-soft', theme.bgSoft);
    r.style.setProperty('--c-surface', theme.surface);
    r.style.setProperty('--c-ink', theme.ink);
    r.style.setProperty('--c-mute', theme.mute);
    r.style.setProperty('--c-border', theme.border);
    r.style.setProperty('--font-display', FONT_STACKS[t.displayFont] || FONT_STACKS['Archivo Black']);
    r.dataset.bgMode = t.bgMode;
  }, [t.primaryColor, t.bgMode, t.displayFont]);

  const scrollTo = (id) => {
    const el = id === 'top' ? document.body : document.getElementById(id);
    if (!el) return;
    if (id === 'top') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      const y = el.getBoundingClientRect().top + window.scrollY - 60;
      window.scrollTo({ top: y, behavior: 'smooth' });
    }
  };

  const marqueeItems = [
    'NUEVOS LINKS CADA DÍA',
    'ENVÍO 7–15 DÍAS',
    'SUB 20€ MAYORÍA',
    'SOPORTE 1 A 1 EN TELEGRAM',
    'SIN PASARELAS RAROS',
    'GUÍAS DE TALLAS',
  ];

  return (
    <div className="page">
      <Navbar onScrollTo={scrollTo} />
      <Hero heroCopy={t.heroCopy} onScrollTo={scrollTo} palette={palette} />
      <Marquee items={marqueeItems} />
      <HowToBuy />
      <Catalog density={t.density} palette={palette} />
      <TelegramBlock />
      <Guides />
      <FAQ />
      <Footer />

      <TweaksPanel>
        <TweakSection label="Color" />
        <TweakColor
          label="Acento"
          value={t.primaryColor}
          options={['#1E3FBE', '#0A0A12', '#E63A2E', '#1F8A5B', '#7B5CFF']}
          onChange={(v) => setTweak('primaryColor', v)}
        />
        <TweakRadio
          label="Fondo"
          value={t.bgMode}
          options={['warm', 'cool', 'paper', 'dark']}
          onChange={(v) => setTweak('bgMode', v)}
        />
        <TweakSection label="Tipografía" />
        <TweakSelect
          label="Display"
          value={t.displayFont}
          options={['Archivo Black', 'Bowlby One', 'Anton', 'Space Grotesk']}
          onChange={(v) => setTweak('displayFont', v)}
        />
        <TweakSection label="Layout" />
        <TweakRadio
          label="Densidad"
          value={t.density}
          options={['compact', 'regular', 'comfy']}
          onChange={(v) => setTweak('density', v)}
        />
        <TweakSection label="Copy" />
        <TweakText
          label="Sub hero"
          value={t.heroCopy}
          onChange={(v) => setTweak('heroCopy', v)}
        />
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
