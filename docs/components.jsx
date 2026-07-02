// TRENT — componentes de secciones
// Usa window.TRENT_DATA y los Tweak* del panel global

const { useState, useEffect, useMemo, useRef } = React;

/* ============================================================
   DISCOUNT BAR — barra anuncio con código
   ============================================================ */
function DiscountBar() {
  const { editMode, cfg, onSave } = React.useContext(window.EditCtx);
  const E = window.EditableText;
  const [copied, setCopied] = useState(false);
  const copy = () => {
    try { navigator.clipboard.writeText(cfg.discountCode); } catch {}
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div className="discountbar">
      <div className="discountbar__inner">
        <span className="discountbar__gift">🎁</span>
        <span className="discountbar__msg">
          <strong>−<E tag="span" value={cfg.discountPct} fieldKey="discountPct" editMode={editMode} onSave={onSave} />%</strong> en tu 1ª compra — código
        </span>
        <button className="discountbar__code" onClick={copy} title="Copiar código">
          <E tag="span" className="discountbar__code-text" value={cfg.discountCode} fieldKey="discountCode" editMode={editMode} onSave={onSave} />
          <span className="discountbar__code-copy">{copied ? '✓ copiado' : 'copiar'}</span>
        </button>
        <E tag="span" className="discountbar__msg discountbar__msg--right" value={cfg.shippingText} fieldKey="shippingText" editMode={editMode} onSave={onSave} />
      </div>
    </div>
  );
}

/* ============================================================
   HERO IMAGE SLIDER
   ============================================================ */
function HeroImageSlider({ images }) {
  const [idx, setIdx] = React.useState(0);
  const startX = React.useRef(null);

  const prev = () => setIdx(i => (i - 1 + images.length) % images.length);
  const next = () => setIdx(i => (i + 1) % images.length);

  const onTouchStart = (e) => { startX.current = e.touches[0].clientX; };
  const onTouchEnd = (e) => {
    if (startX.current === null) return;
    const dx = e.changedTouches[0].clientX - startX.current;
    if (dx > 40) prev();
    else if (dx < -40) next();
    startX.current = null;
  };

  return (
    <div className="hero__product hero__slider"
      onTouchStart={onTouchStart}
      onTouchEnd={onTouchEnd}
      style={{ position: 'relative', overflow: 'hidden', borderRadius: 12, cursor: 'grab' }}>
      {images.map((src, i) => (
        <img key={i} src={src} alt={`producto ${i+1}`}
          style={{
            position: i === 0 ? 'relative' : 'absolute',
            inset: 0, width: '100%', height: '100%',
            objectFit: 'cover', display: 'block',
            opacity: idx === i ? 1 : 0,
            transition: 'opacity 0.35s ease',
          }} />
      ))}
      {/* Badge NEW */}
      <div style={{ position: 'absolute', top: 10, left: 10, background: 'var(--c-primary)', color: '#fff', fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', padding: '3px 10px', borderRadius: 999, zIndex: 2 }}>NEW</div>
      {/* Arrows */}
      {images.length > 1 && <>
        <button onClick={prev} style={{ position:'absolute', left:8, top:'50%', transform:'translateY(-50%)', background:'rgba(255,255,255,0.85)', border:'none', borderRadius:'50%', width:28, height:28, fontSize:14, cursor:'pointer', zIndex:2, display:'flex', alignItems:'center', justifyContent:'center' }}>‹</button>
        <button onClick={next} style={{ position:'absolute', right:8, top:'50%', transform:'translateY(-50%)', background:'rgba(255,255,255,0.85)', border:'none', borderRadius:'50%', width:28, height:28, fontSize:14, cursor:'pointer', zIndex:2, display:'flex', alignItems:'center', justifyContent:'center' }}>›</button>
      </>}
      {/* Dots */}
      <div style={{ position:'absolute', bottom:10, left:'50%', transform:'translateX(-50%)', display:'flex', gap:5, zIndex:2 }}>
        {images.map((_, i) => (
          <button key={i} onClick={() => setIdx(i)} style={{ width: idx===i ? 18 : 6, height:6, borderRadius:999, background: idx===i ? 'var(--c-primary)' : 'rgba(255,255,255,0.7)', border:'none', cursor:'pointer', padding:0, transition:'all 0.2s' }} />
        ))}
      </div>
    </div>
  );
}
window.HeroImageSlider = HeroImageSlider;

/* ============================================================
   CARD IMAGE SLIDER — carrusel ligero para tarjetas de producto
   ============================================================ */
function CardImageSlider({ images, alt }) {
  const [idx, setIdx] = React.useState(0);
  const startX = React.useRef(null);

  const prev = (e) => { e.stopPropagation(); setIdx(i => (i - 1 + images.length) % images.length); };
  const next = (e) => { e.stopPropagation(); setIdx(i => (i + 1) % images.length); };

  const onTouchStart = (e) => { startX.current = e.touches[0].clientX; };
  const onTouchEnd = (e) => {
    if (startX.current === null) return;
    const dx = e.changedTouches[0].clientX - startX.current;
    if (dx > 40) setIdx(i => (i - 1 + images.length) % images.length);
    else if (dx < -40) setIdx(i => (i + 1) % images.length);
    startX.current = null;
  };

  return (
    <div onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}
      style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
      {images.map((src, i) => (
        <img key={i} src={src} alt={`${alt} ${i+1}`}
          style={{
            position: i === 0 ? 'relative' : 'absolute',
            inset: 0, width: '100%', height: '100%',
            objectFit: 'cover', display: 'block',
            opacity: idx === i ? 1 : 0,
            transition: 'opacity 0.35s ease',
          }} />
      ))}
      {images.length > 1 && <>
        <button onClick={prev} style={{ position:'absolute', left:6, top:'50%', transform:'translateY(-50%)', background:'rgba(255,255,255,0.85)', border:'none', borderRadius:'50%', width:24, height:24, fontSize:13, cursor:'pointer', zIndex:2, display:'flex', alignItems:'center', justifyContent:'center' }}>‹</button>
        <button onClick={next} style={{ position:'absolute', right:6, top:'50%', transform:'translateY(-50%)', background:'rgba(255,255,255,0.85)', border:'none', borderRadius:'50%', width:24, height:24, fontSize:13, cursor:'pointer', zIndex:2, display:'flex', alignItems:'center', justifyContent:'center' }}>›</button>
        <div style={{ position:'absolute', bottom:8, left:'50%', transform:'translateX(-50%)', display:'flex', gap:4, zIndex:2 }}>
          {images.map((_, i) => (
            <span key={i} style={{ width: idx===i ? 14 : 5, height:5, borderRadius:999, background: idx===i ? 'var(--c-primary)' : 'rgba(255,255,255,0.7)', transition:'all 0.2s' }} />
          ))}
        </div>
      </>}
    </div>
  );
}
window.CardImageSlider = CardImageSlider;

/* ============================================================
   PLACEHOLDER de imagen (rayado sutil) — el "product shot"
   ============================================================ */
function ProductPlaceholder({ stripe = '#1E3FBE', bg = '#ECECEC', label, drop }) {
  const id = 'pp-' + Math.random().toString(36).slice(2, 8);
  return (
    <svg viewBox="0 0 400 480" preserveAspectRatio="xMidYMid slice" style={{ display: 'block', width: '100%', height: '100%' }}>
      <defs>
        <pattern id={id} width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(35)">
          <rect width="14" height="14" fill={bg} />
          <line x1="0" y1="0" x2="0" y2="14" stroke={stripe} strokeWidth="1" opacity="0.18" />
        </pattern>
      </defs>
      <rect width="400" height="480" fill={`url(#${id})`} />
      <rect x="20" y="20" width="360" height="440" fill="none" stroke={stripe} strokeWidth="1.5" opacity="0.35" strokeDasharray="6 4" />
      <text x="200" y="248" textAnchor="middle" fontFamily="ui-monospace, SFMono-Regular, monospace" fontSize="11" fill={stripe} opacity="0.75" letterSpacing="2">
        PRODUCT · {label?.toUpperCase()}
      </text>
      {drop && (
        <g>
          <rect x="20" y="20" width="56" height="22" fill={stripe} />
          <text x="48" y="35" textAnchor="middle" fontFamily="ui-monospace, monospace" fontSize="11" fontWeight="700" fill="#fff" letterSpacing="1">{drop}</text>
        </g>
      )}
    </svg>
  );
}

/* ============================================================
   MARQUEE
   ============================================================ */
function Marquee({ items = [], speed = 30 }) {
  const content = (
    <div className="marquee-track" style={{ animationDuration: `${speed}s` }}>
      {[...items, ...items, ...items].map((t, i) => (
        <span className="marquee-item" key={i}>
          <span className="marquee-text">{t}</span>
          <span className="marquee-dot">✦</span>
        </span>
      ))}
    </div>
  );
  return <div className="marquee">{content}</div>;
}

/* ============================================================
   NAVBAR
   ============================================================ */
const LANGS = [
  { code: 'es', flag: '🇪🇸', label: 'Español' },
  { code: 'en', flag: '🇬🇧', label: 'English' },
  { code: 'fr', flag: '🇫🇷', label: 'Français' },
  { code: 'it', flag: '🇮🇹', label: 'Italiano' },
  { code: 'pt', flag: '🇵🇹', label: 'Português' },
  { code: 'nl', flag: '🇳🇱', label: 'Nederlands' },
  { code: 'hu', flag: '🇭🇺', label: 'Magyar' },
  { code: 'de', flag: '🇩🇪', label: 'Deutsch' },
];

function LangSelector() {
  const [open, setOpen] = useState(false);
  const ref = React.useRef(null);

  const activeLang = (() => {
    const m = document.cookie.match(/googtrans=\/es\/([a-z]+)/);
    return m ? m[1] : 'es';
  })();
  const active = LANGS.find(l => l.code === activeLang) || LANGS[0];

  const pick = (lang) => {
    const expires = new Date();
    expires.setFullYear(expires.getFullYear() + 1);
    if (lang === 'es') {
      document.cookie = 'googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
      document.cookie = 'googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=.' + location.hostname;
    } else {
      document.cookie = 'googtrans=/es/' + lang + '; expires=' + expires.toUTCString() + '; path=/';
      document.cookie = 'googtrans=/es/' + lang + '; expires=' + expires.toUTCString() + '; path=/; domain=.' + location.hostname;
    }
    location.reload();
  };

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div ref={ref} style={{position:'relative', display:'inline-block'}}>
      <button onClick={() => setOpen(o => !o)} style={{
        display:'flex', alignItems:'center', gap:'6px',
        background:'transparent', border:'1.5px solid currentColor',
        borderRadius:'999px', padding:'4px 8px', cursor:'pointer',
        fontSize:'11px', fontWeight:600, color:'inherit', opacity:0.85,
        whiteSpace:'nowrap'
      }}>
        <span style={{fontSize:'18px', lineHeight:1}} translate="no">{active.flag}</span>
        <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor" style={{opacity:0.6, transform: open ? 'rotate(180deg)' : 'none', transition:'transform 0.2s'}}>
          <path d="M1 3l4 4 4-4"/>
        </svg>
      </button>
      {open && (
        <div style={{
          position:'absolute', right:0, top:'calc(100% + 8px)',
          background:'var(--c-surface, #fff)', border:'1.5px solid var(--c-border, #e5e7eb)',
          borderRadius:'14px', boxShadow:'0 8px 24px rgba(0,0,0,0.12)',
          overflow:'hidden', zIndex:9999, minWidth:'150px'
        }}>
          {LANGS.map(l => (
            <button key={l.code} onClick={() => pick(l.code)} style={{
              display:'flex', alignItems:'center', gap:'10px',
              width:'100%', padding:'10px 16px', border:'none',
              background: l.code === activeLang ? 'var(--c-primary, #000)' : 'transparent',
              color: l.code === activeLang ? '#fff' : 'inherit',
              cursor:'pointer', fontSize:'14px', fontWeight: l.code === activeLang ? 700 : 400,
              textAlign:'left'
            }}>
              <span style={{fontSize:'16px'}}>{l.flag}</span>
              <span>{l.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function Navbar({ onScrollTo }) {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', fn);
    return () => window.removeEventListener('scroll', fn);
  }, []);

  return (
    <nav className={`nav ${scrolled ? 'nav--scrolled' : ''}`}>
      <a href="#top" className="nav__logo" onClick={(e) => { e.preventDefault(); onScrollTo('top'); }}>
        <img src={(window.__resources && window.__resources.trentLogo) || "assets/trent-logo.png"} alt="TRENT Clothing" />
      </a>
      <ul className="nav__links">
        <li><a href="#drops" onClick={(e) => { e.preventDefault(); onScrollTo('drops'); }}>Links</a></li>
        <li><a href="#how" onClick={(e) => { e.preventDefault(); onScrollTo('how'); }}>Cómo comprar</a></li>
        <li><a href="#telegram" onClick={(e) => { e.preventDefault(); onScrollTo('telegram'); }}>Telegram</a></li>
        <li><a href="#guides" onClick={(e) => { e.preventDefault(); onScrollTo('guides'); }}>Guías</a></li>
        <li><a href="#faq" onClick={(e) => { e.preventDefault(); onScrollTo('faq'); }}>FAQ</a></li>
      </ul>
      <div className="nav__actions" style={{display:'flex', alignItems:'center', gap:'8px', marginLeft:'auto'}}>
        <a href="https://t.me/trentthacoo" target="_blank" rel="noreferrer" className="btn btn--primary nav__cta">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>
          Entrar al canal
        </a>
        <LangSelector />
      </div>
    </nav>
  );
}

/* ============================================================
   HERO
   ============================================================ */
function Hero({ onScrollTo, palette }) {
  const { editMode, cfg, onSave } = React.useContext(window.EditCtx);
  const E = window.EditableText;
  const [codeCopied, setCodeCopied] = useState(false);
  return (
    <header id="top" className="hero">
      <div className="hero__grid">
        <div className="hero__left">
          <div className="hero__eyebrow">
            <span className="dot dot--live"></span>
            <E tag="span" value={cfg.heroEyebrow} fieldKey="heroEyebrow" editMode={editMode} onSave={onSave} />
          </div>
          <h1 className="hero__title">
            <span className="hero__title-line hero__title-line--accent">LINKS</span>
            <span className="hero__title-line hero__title-line--outline">HACOO</span>
          </h1>
          <E tag="p" className="hero__sub" value={cfg.heroCopy} fieldKey="heroCopy" editMode={editMode} onSave={onSave} />
          <div className="hero__ctas">
            <a href={cfg.telegramLink} target="_blank" rel="noreferrer" className="btn btn--primary btn--lg">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>
              <E tag="span" value={cfg.heroBtnPrimary} fieldKey="heroBtnPrimary" editMode={editMode} onSave={onSave} />
            </a>
            <button className="btn btn--ghost btn--lg" onClick={() => onScrollTo('drops')}>
              <E tag="span" value={cfg.heroBtnSecondary} fieldKey="heroBtnSecondary" editMode={editMode} onSave={onSave} />
              <span className="btn__arrow">→</span>
            </button>
          </div>
          <div
            className="hero__code-strip"
            role="button" tabIndex={0}
            onClick={() => { try { navigator.clipboard.writeText(cfg.discountCode || 'TRENT14'); } catch {} setCodeCopied(true); setTimeout(() => setCodeCopied(false), 1800); }}
            onKeyDown={e => e.key === 'Enter' && e.currentTarget.click()}
            title="Copiar código"
            autoComplete="off"
          >
            <span className="hero__code-strip-pct" translate="no">−{cfg.discountPct || '14'}%</span>
            <span className="hero__code-strip-sep" />
            <span className="hero__code-strip-label">CÓDIGO DESCUENTO<span className="hero__code-strip-fire">🎁</span>:</span>
            <span className="hero__code-strip-code" translate="no" data-code="TRENT14">{cfg.discountCode || 'TRENT14'}</span>
            <span className="hero__code-strip-copy">{codeCopied ? '✓ Copiado' : 'Copiar'}</span>
          </div>
        </div>
      </div>
    </header>
  );
}

/* ============================================================
   STEPS — Cómo comprar
   ============================================================ */
function HowToBuy() {
  const { editMode, cfg, onSave } = React.useContext(window.EditCtx);
  const E = window.EditableText;
  const steps = [
    { n: '01', title: cfg.step0title, body: cfg.step0body, tag: cfg.step0tag, href: 'https://apps.apple.com/es/app/hacoo-discovering-inspiring/id1399907836', cta: '' },
    { n: '02', title: cfg.step1title, body: cfg.step1body, tag: cfg.step1tag, href: 'https://t.me/trentthacoo', cta: '' },
    { n: '03', title: cfg.step2title, body: cfg.step2body, tag: cfg.step2tag, href: '#drops', cta: '' },
    { n: '04', title: cfg.step3title, body: cfg.step3body, tag: cfg.step3tag, href: '#', cta: 'copiar', isCopyCode: true },
  ];
  return (
    <section id="how" className="section section--how">
      <div className="section__head">
        <div className="section__eyebrow">[ 02 ] PROCESO</div>
        <E tag="h2" className="section__title" value={cfg.howTitle} fieldKey="howTitle" editMode={editMode} onSave={onSave} />
        <E tag="p" className="section__lead" value={cfg.howLead} fieldKey="howLead" editMode={editMode} onSave={onSave} />
      </div>
      <ol className="steps">
        {steps.map((s, i) => (
          <li key={s.n} className="step">
            <a
              className="step__link"
              href={s.href}
              target={s.isCopyCode ? undefined : "_blank"}
              rel={s.isCopyCode ? undefined : "noreferrer"}
              onClick={s.isCopyCode ? (e) => {
                e.preventDefault();
                navigator.clipboard.writeText('TRENT14');
                alert('Código copiado: TRENT14');
              } : (editMode ? e => e.preventDefault() : undefined)}
            >
              <div className="step__n">{s.n}</div>
              <div className="step__body">
                <E tag="h3" className="step__title" value={s.title} fieldKey={`step${i}title`} editMode={editMode} onSave={onSave} />
                <E tag="p" className="step__desc" value={s.body} fieldKey={`step${i}body`} editMode={editMode} onSave={onSave} />
                <div className="step__foot">
                  <E tag="span" className="step__tag" value={s.tag} fieldKey={`step${i}tag`} editMode={editMode} onSave={onSave} />
                  <span className="step__cta">{s.cta}</span>
                </div>
              </div>
            </a>
          </li>
        ))}
      </ol>
    </section>
  );
}

/* ============================================================
   CATÁLOGO — filtros + grid + wishlist + paginación
   ============================================================ */
// Unifica variantes de la misma marca (mayúsculas, abreviaturas, acentos...)
const BRAND_ALIASES = {
  'a bathing ape': 'Bape',
  'bape': 'Bape',
  'cp company': 'C.P. Company',
  'c.p. company': 'C.P. Company',
  'c. p. company': 'C.P. Company',
  'co company': 'C.P. Company',
  'ami': 'Ami Paris',
  'ami paris': 'Ami Paris',
  'longchamp': 'Longchamp',
  'on': 'On Cloud',
  'on cloud': 'On Cloud',
  'synaworld': 'Synaworld',
  'syna world': 'Synaworld',
  'syna word': 'Synaworld',
  'polene': 'Polène',
  'polène': 'Polène',
  'aime leon dore': 'Aimé Leon Dore',
  'aimé leon dore': 'Aimé Leon Dore',
  'off white': 'Off-White',
  'off-white': 'Off-White',
  'poedagar': 'Poedegar',
  'poedegar': 'Poedegar',
  'miu mui': 'Miu Miu',
  'miu miu': 'Miu Miu',
  'acne studio': 'Acne Studios',
  'acne studios': 'Acne Studios',
  'aimana': 'Aimana',
  'fear of god': 'Essentials FOG',
  'essentials fog': 'Essentials FOG',
  'fenty': 'Fenty Beauty',
  'fenty beauty': 'Fenty Beauty',
};
// Une variantes de la misma marca y separa campos con varias marcas ("Adidas, Gucci", "Bape x Nike")
function normalizeBrand(brand) {
  const key = (brand || '').trim().toLowerCase();
  return BRAND_ALIASES[key] || (brand || '').trim();
}
const LETTER_RANGES = ['A-C', 'D-F', 'G-I', 'J-L', 'M-O', 'P-R', 'S-U', 'V-Z'];
function splitBrands(raw) {
  if (!raw) return [];
  return raw.split(/\s*,\s*|\s+x\s+/i).map(normalizeBrand).filter(Boolean);
}

// Detecta categoría desde el nombre del producto
function detectCat(name, savedCat, isManual) {
  // Si se ha fijado manualmente desde el admin, se respeta
  if (isManual && savedCat) return savedCat;
  // Si no, se detecta automáticamente por el nombre
  // Normalize accents: á→a, é→e, í→i, ó→o, ú→u
  const n = (name || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  if (/futbol|football|soccer|balon|equipacion|champions|copa|liga\b|mundial|seleccion|titular|visitante|retro shirt|camiseta retro|jersey club|kit de futbol|camiseta del|camiseta de futbol|real madrid|barcelona|barca\b|atletico de madrid|atletico madrid|psg|paris saint|manchester|man city|man united|liverpool|chelsea|arsenal|tottenham|bayern|dortmund|juventus|inter de milan|ac milan|napoli|roma\b|brasil|argentina|francia\b|alemania\b|italia\b|portugal\b|espana\b|holanda\b|inglaterra\b|croacia\b|nike futbol|adidas futbol/.test(n)) return 'Fútbol ⚽';
  if (/conjunto|tracksuit|(?<!pantalon )chandal|two piece|two-piece|set de\b|outfit set/.test(n)) return 'Conjuntos';
  if (/zapati|zapato|sneaker|zapatill|boot|bota|shoe|calzad|sandalia|chancla|zueco|mocasin|bailarina|\bshox\b|\bair max\b|\bair force\b|\bdunk\b|\bjordan\b|\baf1\b|\bnmd\b|\bultraboost\b|\bboost\b|\bforum\b|\bstan smith\b|\bsuperstar\b|\bclassic leather\b|\bnb\s*\d{3,4}\b|\b574\b|\b990\b|\b991\b|\b992\b|\b993\b|\b996\b|\b997\b|\b998\b|\b1080\b|\b2002r\b|\b327\b|\b530\b|\b550\b|\b9060\b|\b1906r?\b|\b860\b|\b880\b|\bfree run\b|\bpegasus\b|\bcortez\b|\bblazar\b|\bmetcon\b|\breact\b|\bwaffle\b|\bterrascape\b|\bozweego\b|\brs-x\b|\bsuede\b|\bcali\b|\bmayze\b|\bclyde\b|\bgel[-\s]|\bgt[-\s]\d|\bkayano\b|\bpuma\s*\d{3}\b|\bvomero\b|\bnocta\b|\bair tn\b|\bair plus\b|\b\btn\b|\bp6000\b|\bsndr\b|\buptempo\b|\bmind 001\b|\bnike mind\b|\bmoon sp\b|\bara rover\b|\btotal 90\b|\bmk2\b|\bnvr\b|\bnocta glide\b|\bhot step\b|\bsb dunk\b|\bsb colabo/.test(n)) return 'Zapatillas/Zapatos';
  if (/camiseta|tee|tshirt|polo|shirt|camisa|top\b/.test(n)) return 'Camisetas';
  if (/hoodie|sudadera|sweat|jersey|crewneck/.test(n)) return 'Sudaderas';
  if (/pantalon|jean|denim|cargo|jogger|short|bermuda|vaquero/.test(n)) return 'Pantalones';
  if (/puffer|chaqueton|parka|trench|abrigo largo|abrigo de plumas|plumifero|plumon/.test(n)) return 'Puffer/Chaquetón';
  if (/chaqueta|jacket|abrigo|coat|blazer|chaleco|cortavientos|chubasquero|windbreaker|raincoat|impermeable/.test(n)) return 'Chaquetas';
  if (/mochila|rinonera|fanny pack|fanny bag|waist bag|belt bag|backpack|cangurera|sling bag/.test(n)) return 'Mochilas/Riñoneras';
  if (/bolso|bolsa|bag|tote|clutch|cartera/.test(n)) return 'Bolsos/Bolsas';
  if (/vestido|dress|falda|skirt/.test(n)) return 'Vestidos';
  if (/gorro|hat|cap|gorra|beanie|bucket|sombrero/.test(n)) return 'Gorras/Gorros';
  if (/scrunchie/.test(n)) return 'Accesorios';
  if (/cinturon|belt|collar|pulsera|anillo|ring|joya|jewel|bufanda|scarf|reloj|(?<!apple )(?<!smart)watch/.test(n)) return 'Accesorios';
  if (/auricular|airpod|earbud|earphone|headphone|altavoz|speaker|iphone|ipad|macbook|apple watch|smartwatch|airtag|cargador|charger|powerbank|electronic|dyson|proyector|projector|microfono|microphone|\bmic\b/.test(n)) return 'Electrónica';
  if (/maquillaje|makeup|make up|labial|lipstick|gloss|pintalabios|base de maquillaje|foundation|corrector|concealer|rimel|rimmel|mascara de pestanas|sombra de ojos|eyeshadow|delineador|eyeliner|colorete|blush|bronceador|bronzer|iluminador|highlighter|polvos compactos|prebase|primer|paleta de maquillaje|brocha de maquillaje|beauty blender|cosmetic/.test(n)) return 'Maquillaje 💄';
  if (/birkenstock|golden goose|\bhoka\b|onitsuka|mizuno|saucony|\basics\b|\bautry\b|yeezy|\bveja\b|\bcrocs\b|new balance|\bvans\b|\breebok\b|salomon|dr martens|\bmartens\b|\bconverse\b|havaianas|\bugg\b|on cloud|adidas spezial|adidas samba|adidas gazelle|adidas campus/.test(n)) return 'Zapatillas/Zapatos';
  return 'Otros';
}

function Catalog({ density, palette }) {
  const ctx = React.useContext(window.EditCtx || React.createContext({ editMode: false, cfg: {}, onSave: () => {} }));
  const editMode = ctx ? ctx.editMode : false;
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const itemsPerPage = density === 'compact' ? 20 : density === 'comfy' ? 12 : 16;

  const [cat, setCat] = useState([]);
  const [brand, setBrand] = useState([]);
  const [fuente, setFuente] = useState('Todas');
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [filterOpen, setFilterOpen] = useState(false);
  const [wishlist, setWishlist] = useState(() => {
    try { return JSON.parse(localStorage.getItem('trent_wishlist') || '[]'); } catch { return []; }
  });
  const [toast, setToast] = useState(null);
  const [lightbox, setLightbox] = useState(null);
  const [quickView, setQuickView] = useState(null);
  const [showWishlistOnly, setShowWishlistOnly] = useState(false);
  const [letterRange, setLetterRange] = useState('Todas');

  useEffect(() => {
    if (!window._db) { setLoading(false); return; }
    const unsub = window._db.collection('products')
      .onSnapshot((snap) => {
        const docs = snap.docs.map((d) => ({ id: d.id, ...d.data() }));
        setProducts(docs);
        setLoading(false);
      }, () => setLoading(false));
    return () => unsub();
  }, []);

  useEffect(() => {
    localStorage.setItem('trent_wishlist', JSON.stringify(wishlist));
    if (wishlist.length === 0) setShowWishlistOnly(false);
  }, [wishlist]);

  const brands = useMemo(() => {
    const set = new Set(products.flatMap(p => splitBrands(p.marca || p.brand || '')));
    return ['Todas', ...Array.from(set).sort()];
  }, [products]);

  const visibleBrands = useMemo(() => {
    if (letterRange === 'Todas') return brands;
    const [from, to] = letterRange.split('-');
    return brands.filter((b) => {
      if (b === 'Todas') return true;
      const ch = b[0].toUpperCase();
      return ch >= from && ch <= to;
    });
  }, [brands, letterRange]);

  const cats = useMemo(() => {
    const set = new Set(products.map(p => detectCat(p.nom || p.name || '', p.categoria, p.categoriaManual)));
    return ['Todo', ...Array.from(set).sort()];
  }, [products]);

  const filtered = useMemo(() => {
    return products.filter((p) => {
      const name = p.nom || p.name || '';
      const brandVals = splitBrands(p.marca || p.brand || '');
      if (showWishlistOnly && !wishlist.includes(p.id)) return false;
      if (brand.length > 0 && !brand.some(b => brandVals.includes(b))) return false;
      if (cat.length > 0 && !cat.includes(detectCat(name, p.categoria, p.categoriaManual))) return false;
      if (fuente !== 'Todas' && (p.fuente || 'Hacoo') !== fuente) return false;
      if (q && !name.toLowerCase().includes(q.toLowerCase())) return false;
      return true;
    }).sort((a, b) => {
      const da = a.destacado ? 1 : 0;
      const db = b.destacado ? 1 : 0;
      if (db !== da) return db - da;
      if (da && db) {
        const oa = typeof a.orden === 'number' ? a.orden : Infinity;
        const ob = typeof b.orden === 'number' ? b.orden : Infinity;
        if (oa !== ob) return oa - ob;
      }
      const ta = a.data && a.data.toMillis ? a.data.toMillis() : (a.data && a.data.seconds ? a.data.seconds * 1000 : 0);
      const tb = b.data && b.data.toMillis ? b.data.toMillis() : (b.data && b.data.seconds ? b.data.seconds * 1000 : 0);
      return tb - ta;
    });
  }, [products, brand, cat, q, fuente, showWishlistOnly, wishlist]);

  const totalPages = Math.ceil(filtered.length / itemsPerPage);
  const paginated = filtered.slice((page - 1) * itemsPerPage, page * itemsPerPage);

  const toggleWish = (id) => {
    setWishlist((w) => w.includes(id) ? w.filter((x) => x !== id) : [...w, id]);
  };

  const resetPagination = () => setPage(1);

  const activeFilters = brand.length + cat.length;

  const clearFilters = () => { setBrand([]); setCat([]); setFuente('Todas'); resetPagination(); };

  const toggleCat = (c) => {
    if (c === 'Todo') { setCat([]); resetPagination(); return; }
    setCat((prev) => prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]);
    resetPagination();
  };

  const toggleBrand = (b) => {
    if (b === 'Todas') { setBrand([]); resetPagination(); return; }
    setBrand((prev) => prev.includes(b) ? prev.filter((x) => x !== b) : [...prev, b]);
    resetPagination();
  };

  return (
    <section id="drops" className={`section section--catalog density--${density}`}>
      <div className="section__head" style={{ marginBottom: 22 }}>
        <div className="section__eyebrow" style={{ marginBottom: 8 }}>[ 01 ] CATÁLOGO</div>
        <h2 className="section__title" style={{ fontSize: 'clamp(28px, 6vw, 48px)', whiteSpace: 'nowrap', marginBottom: 8 }}>Links <em>Productos</em>.</h2>
        <p className="section__lead">{loading ? 'Cargando…' : `${filtered.length} prendas disponibles. Filtra por marca o en el buscador.`}</p>
      </div>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 20 }}>
        <div className="catalog__search" style={{ flex: 1, minWidth: 0 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.5" y2="16.5"/></svg>
          <input placeholder="Busca hoodie, sneaker…" value={q} onChange={(e) => { setQ(e.target.value); resetPagination(); }} />
          {q && <button className="catalog__clear" onClick={() => { setQ(''); resetPagination(); }}>×</button>}
        </div>
        <button className="catalog__filter-btn" onClick={() => setFilterOpen(o => !o)} style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, padding: '12px 18px',
          border: `2px solid var(--c-primary)`, flex: 1,
          borderRadius: 999, background: activeFilters > 0 ? 'var(--c-primary)' : 'var(--c-surface)',
          color: activeFilters > 0 ? '#fff' : 'var(--c-primary)',
          fontFamily: 'inherit', fontSize: 14, fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap',
        }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="4" y1="6" x2="20" y2="6"/><line x1="8" y1="12" x2="16" y2="12"/><line x1="11" y1="18" x2="13" y2="18"/></svg>
          Filtrar {activeFilters > 0 ? `(${activeFilters})` : ''}
        </button>
      </div>

      {filterOpen && (
        <div style={{
          background: 'var(--c-surface)', border: '1.5px solid var(--c-border)',
          borderRadius: 14, padding: '20px 24px', marginBottom: 20,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <span style={{ fontWeight: 700, fontSize: 14 }}>Filtros</span>
            {activeFilters > 0 && (
              <button onClick={clearFilters} style={{ background: 'none', border: 'none', color: 'var(--c-primary)', fontFamily: 'inherit', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                Limpiar filtros
              </button>
            )}
          </div>
          <div className="filter-group" style={{ marginBottom: 16 }}>
            <span className="filter-label">Tipo de prenda</span>
            <div className="chips">
              {cats.map((c) => (
                <button key={c} className={`chip ${(c === 'Todo' ? cat.length === 0 : cat.includes(c)) ? 'chip--active' : ''}`} onClick={() => toggleCat(c)}>
                  {c}
                </button>
              ))}
            </div>
          </div>
          <div className="filter-group">
            <span className="filter-label">Marca</span>
            <div className="chips" style={{ marginBottom: 10 }}>
              <button
                className={`chip ${letterRange === 'Todas' ? 'chip--active' : ''}`}
                onClick={() => setLetterRange('Todas')}
              >Todas</button>
              {LETTER_RANGES.map((r) => (
                <button
                  key={r}
                  className={`chip ${letterRange === r ? 'chip--active' : ''}`}
                  onClick={() => setLetterRange(r)}
                >{r}</button>
              ))}
            </div>
            {letterRange !== 'Todas' && (
              <div className="chips">
                {visibleBrands.map((b) => (
                  <button key={b} className={`chip ${(b === 'Todas' ? brand.length === 0 : brand.includes(b)) ? 'chip--active' : ''}`} onClick={() => toggleBrand(b)}>
                    {b}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="filter-group" style={{ marginTop: 12 }}>
            <span className="filter-label">Plataforma</span>
            <div className="chips" style={{ marginBottom: 0 }}>
              {['Todas', 'Hacoo', 'Yepexpress'].map(f => (
                <button key={f} className={`chip ${fuente === f ? 'chip--active' : ''}`} onClick={() => { setFuente(f); resetPagination(); }}>{f}</button>
              ))}
            </div>
          </div>
        </div>
      )}

      {wishlist.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <button className="wishlist-badge" onClick={() => { setShowWishlistOnly((v) => !v); resetPagination(); }}>
            {showWishlistOnly ? '← Ver todo el catálogo' : `♥ ${wishlist.length} en wishlist · ver`}
          </button>
          {showWishlistOnly && (
            <button className="wishlist-badge" onClick={() => { setWishlist([]); setShowWishlistOnly(false); }}>
              Borrar wishlist
            </button>
          )}
        </div>
      )}

      <div className="grid">
        {loading && (
          <div className="empty">
            <div className="empty__big">Cargando productos…</div>
          </div>
        )}
        {!loading && paginated.map((p) => {
          const name = p.nom || p.name || '';
          const price = p.preu || p.price || '';
          const brand = p.marca || p.brand || '';
          const imgUrl = p.imatge || p.image_url || '';
          const imgList = (Array.isArray(p.imagenes) && p.imagenes.length > 0) ? p.imagenes : (imgUrl ? [imgUrl] : []);
          const link = p.link_afiliats || p.link || 'https://t.me/trentthacoo';
          const fuente = p.fuente || 'Hacoo';

          const saveProduct = async (field, value) => {
            if (!window._db) return;
            await window._db.collection('products').doc(p.id).update({ [field]: value });
          };

          const changeImage = () => {
            const url = prompt('URL de la nueva imagen:', imgUrl);
            if (url !== null) saveProduct('imatge', url);
          };

          return (
            <article key={p.id} className="card">
              <div className="card__img" style={{ position: 'relative', cursor: !editMode ? 'pointer' : 'default' }}
                onClick={() => { if (!editMode) setQuickView({ id: p.id, name, price, brand, imgList, link, fuente }); }}>
                {imgList.length > 0
                  ? <CardImageSlider images={imgList} alt={name} />
                  : <ProductPlaceholder stripe="#1E3FBE" bg="#ECECEC" label={name} />
                }
                <span style={{
                  position: 'absolute', top: 8, right: 8, zIndex: 2,
                  background: fuente === 'Yepexpress' ? '#FF6B00' : '#1E3FBE',
                  color: '#fff', fontSize: 8, fontWeight: 700, letterSpacing: '0.5px',
                  padding: '2px 5px', borderRadius: 999, pointerEvents: 'none',
                }}>{fuente}</span>
                {editMode && (
                  <button onClick={(e) => { e.stopPropagation(); changeImage(); }} style={{
                    position: 'absolute', inset: 0, width: '100%', height: '100%',
                    background: 'rgba(30,63,190,.55)', color: '#fff', border: 'none',
                    cursor: 'pointer', fontFamily: 'inherit', fontSize: 13, fontWeight: 600,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                  }}>
                    🖼️ Cambiar foto
                  </button>
                )}
                {editMode && (
                  <button
                    onClick={(e) => { e.stopPropagation(); saveProduct('destacado', !p.destacado); }}
                    title={p.destacado ? 'Quitar de destacados' : 'Destacar (mostrar primero)'}
                    style={{
                      position: 'absolute', top: 10, right: 10, zIndex: 3,
                      background: p.destacado ? 'var(--c-primary)' : 'rgba(255,255,255,0.9)',
                      color: p.destacado ? '#fff' : '#0A0A12',
                      border: 'none', borderRadius: '50%', width: 32, height: 32, fontSize: 16,
                      cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                    {p.destacado ? '★' : '☆'}
                  </button>
                )}
                {!editMode && (
                  <button
                    className={`card__wish ${wishlist.includes(p.id) ? 'card__wish--on' : ''}`}
                    onClick={(e) => { e.stopPropagation(); toggleWish(p.id); }}
                    aria-label="Guardar"
                  >
                    {wishlist.includes(p.id) ? '♥' : '♡'}
                  </button>
                )}
              </div>
              <div className="card__body">
                <div className="card__row" style={{ marginBottom: 12 }}>
                  {editMode
                    ? <span contentEditable suppressContentEditableWarning
                        style={{ outline: '2px dashed #1E3FBE', borderRadius: 4, padding: '1px 4px', minWidth: 10 }}
                        onBlur={e => saveProduct('marca', e.currentTarget.textContent.trim())}
                      >{brand}</span>
                    : <div className="card__cat">{splitBrands(brand).join(' · ') || brand}</div>
                  }
                  {editMode
                    ? <span contentEditable suppressContentEditableWarning
                        style={{ outline: '2px dashed #1E3FBE', borderRadius: 4, padding: '1px 4px', minWidth: 10, fontWeight: 700 }}
                        onBlur={e => saveProduct('preu', e.currentTarget.textContent.trim())}
                      >{price}</span>
                    : <div className="card__price">{price}</div>
                  }
                </div>
                {editMode
                  ? <h3 className="card__name" contentEditable suppressContentEditableWarning
                      style={{ outline: '2px dashed #1E3FBE', borderRadius: 4, cursor: 'text' }}
                      onBlur={e => saveProduct('nom', e.currentTarget.textContent.trim())}
                    >{name}</h3>
                  : <h3 className="card__name" style={{ cursor: 'pointer', display: 'block', fontSize: 17, lineHeight: 1.3, marginBottom: 16 }} onClick={() => setQuickView({ id: p.id, name, price, brand, imgList, link, fuente })}>{name}</h3>
                }
                {!editMode && (
                  <div className="card__actions">
                    <a href={link} target="_blank" rel="noreferrer" className="card__btn card__btn--primary">
                      Comprar →
                    </a>
                    <button className="card__btn card__btn--ghost" onClick={() => { try { navigator.clipboard.writeText(link); } catch {} setToast(`Link copiado · ${name}`); setTimeout(() => setToast(null), 1800); }} title="Copiar link">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                    </button>
                  </div>
                )}
                {editMode && (
                  <div className="card__actions">
                    <span contentEditable suppressContentEditableWarning
                      style={{ outline: '2px dashed #1E3FBE', borderRadius: 4, padding: '1px 4px', fontSize: 12, flex: 1 }}
                      onBlur={e => saveProduct('link_afiliats', e.currentTarget.textContent.trim())}
                      title="Editar link"
                    >{link}</span>
                  </div>
                )}
              </div>
            </article>
          );
        })}
        {!loading && filtered.length === 0 && (
          <div className="empty">
            <div className="empty__big">{products.length === 0 ? 'Aún no hay productos' : 'Sin resultados'}</div>
            <div className="empty__sub">{products.length === 0 ? 'Los productos aparecerán aquí cuando el bot publique en el canal.' : 'Intenta con otro filtro o búsqueda.'}</div>
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button className="pagination__btn" disabled={page === 1} onClick={() => setPage(page - 1)}>← Anterior</button>
          <div className="pagination__info">
            Página <strong>{page}</strong> de <strong>{totalPages}</strong>
          </div>
          <button className="pagination__btn" disabled={page === totalPages} onClick={() => setPage(page + 1)}>Siguiente →</button>
        </div>
      )}

      {toast && <div className="toast">{toast}</div>}

      {quickView && (
        <div onClick={() => setQuickView(null)} style={{
          position: 'fixed', inset: 0, background: 'rgba(10,10,18,0.75)', zIndex: 900,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
        }}>
          <div onClick={(e) => e.stopPropagation()} style={{
            width: 'min(92vw, 420px)', maxHeight: '90vh', overflowY: 'auto',
            background: 'var(--c-surface)', borderRadius: 16, position: 'relative',
          }}>
            <button onClick={() => setQuickView(null)} aria-label="Cerrar" style={{
              position: 'absolute', top: 10, right: 10, zIndex: 2, background: 'rgba(255,255,255,0.9)', border: 'none',
              borderRadius: '50%', width: 36, height: 36, fontSize: 18, cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>×</button>
            <button
              className={`card__wish ${wishlist.includes(quickView.id) ? 'card__wish--on' : ''}`}
              onClick={() => toggleWish(quickView.id)}
              aria-label="Guardar"
              style={{ position: 'absolute', top: 10, left: 10, zIndex: 2 }}
            >
              {wishlist.includes(quickView.id) ? '♥' : '♡'}
            </button>
            <div
              style={{ width: '100%', height: 'min(92vw, 420px)', borderRadius: '16px 16px 0 0', overflow: 'hidden', cursor: quickView.imgList.length > 0 ? 'zoom-in' : 'default' }}
              onClick={() => { if (quickView.imgList.length > 0) setLightbox({ images: quickView.imgList, alt: quickView.name }); }}
            >
              {quickView.imgList.length > 0
                ? <CardImageSlider images={quickView.imgList} alt={quickView.name} />
                : <ProductPlaceholder stripe="#1E3FBE" bg="#ECECEC" label={quickView.name} />
              }
            </div>
            <div style={{ padding: '20px 22px 24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <div className="card__cat">{splitBrands(quickView.brand).join(' · ') || quickView.brand}</div>
                <span style={{
                  background: quickView.fuente === 'Yepexpress' ? '#FF6B00' : '#1E3FBE',
                  color: '#fff', fontSize: 11, fontWeight: 700, letterSpacing: '0.5px',
                  padding: '4px 9px', borderRadius: 999,
                }}>{quickView.fuente || 'Hacoo'}</span>
              </div>
              <h3 className="card__name" style={{ fontSize: 21, lineHeight: 1.25, marginBottom: 10 }}>{quickView.name}</h3>
              <div className="card__price" style={{ fontSize: 22, marginBottom: 20 }}>{quickView.price}</div>
              <div className="card__actions">
                <a href={quickView.link} target="_blank" rel="noreferrer" className="card__btn card__btn--primary">
                  Comprar →
                </a>
                <button className="card__btn card__btn--ghost" onClick={() => { try { navigator.clipboard.writeText(quickView.link); } catch {} setToast(`Link copiado · ${quickView.name}`); setTimeout(() => setToast(null), 1800); }} title="Copiar link">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {lightbox && (
        <div onClick={() => setLightbox(null)} style={{
          position: 'fixed', inset: 0, background: 'rgba(10,10,18,0.85)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
        }}>
          <button onClick={() => setLightbox(null)} aria-label="Cerrar" style={{
            position: 'absolute', top: 18, right: 18, background: 'rgba(255,255,255,0.9)', border: 'none',
            borderRadius: '50%', width: 36, height: 36, fontSize: 18, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>×</button>
          <div onClick={(e) => e.stopPropagation()} style={{
            width: 'min(92vw, 520px)', height: 'min(92vw, 520px)', borderRadius: 16, overflow: 'hidden',
          }}>
            <CardImageSlider images={lightbox.images} alt={lightbox.alt} />
          </div>
        </div>
      )}
    </section>
  );
}

/* ============================================================
   TELEGRAM block
   ============================================================ */
function TelegramBlock() {
  const { editMode, cfg, onSave } = React.useContext(window.EditCtx);
  const E = window.EditableText;

  const benefits = [
    { ic: '📌', tKey: 'benefit0t', sKey: 'benefit0s' },
    { ic: '⚡', tKey: 'benefit1t', sKey: 'benefit1s' },
    { ic: '🛟', tKey: 'benefit2t', sKey: 'benefit2s' },
    { ic: '🔓', tKey: 'benefit3t', sKey: 'benefit3s' },
  ];

  return (
    <section id="telegram" className="section section--telegram">
      <div className="telegram__inner">
        <div className="telegram__left">
          <div className="section__eyebrow section__eyebrow--light">[ 03 ] EL CANAL</div>
          <E tag="h2" className="section__title section__title--light" value={cfg.telegramTitle} fieldKey="telegramTitle" editMode={editMode} onSave={onSave} />
          <E tag="p" className="section__lead section__lead--light" value={cfg.telegramLead} fieldKey="telegramLead" editMode={editMode} onSave={onSave} />
          <a href={cfg.telegramLink} target="_blank" rel="noreferrer" className="btn btn--invert btn--lg">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>
            <E tag="span" value={cfg.telegramLink} fieldKey="telegramLink" editMode={editMode} onSave={onSave} />
          </a>
          <E tag="div" className="telegram__handle" value={cfg.telegramMembers} fieldKey="telegramMembers" editMode={editMode} onSave={onSave} />
        </div>
        <div className="telegram__right">
          {benefits.map((b, i) => (
            <div key={i} className="benefit" style={{flexDirection:'row', alignItems:'center', padding:'14px 16px', gap:'14px', minHeight:0}}>
              <div className="benefit__ic" style={{fontSize:'22px', flexShrink:0}}>{b.ic}</div>
              <div style={{display:'flex', flexDirection:'column', gap:'2px'}}>
                <E className="benefit__t" style={{fontSize:'14px'}} value={cfg[b.tKey]} fieldKey={b.tKey} editMode={editMode} onSave={onSave} />
                <E className="benefit__s" style={{fontSize:'12px', opacity:0.7}} value={cfg[b.sKey]} fieldKey={b.sKey} editMode={editMode} onSave={onSave} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   SIZE CALCULATOR
   ============================================================ */
function SizeCalculator() {
  const [height, setHeight] = useState(175);
  const [weight, setWeight] = useState(72);
  const [fit, setFit] = useState('regular');

  const size = useMemo(() => {
    // Peso como factor principal (fuente: O'Neill, VadeRetro, marcas deportivas)
    const SIZES = ['XS','S','M','L','XL','XXL','3XL'];
    let idx = 0;

    if (weight < 55)       idx = 0; // XS
    else if (weight < 65)  idx = 1; // S
    else if (weight < 78)  idx = 2; // M
    else if (weight < 92)  idx = 3; // L
    else if (weight < 108) idx = 4; // XL
    else if (weight < 125) idx = 5; // XXL
    else                   idx = 6; // 3XL

    // Altura ajusta ±1: si eres muy alto sube talla, muy bajo baja
    if (height >= 188) idx = Math.min(idx + 1, 6);
    else if (height < 163) idx = Math.max(idx - 1, 0);

    // Fit adjustment
    if (fit === 'baggy') idx = Math.min(idx + 1, 6);
    if (fit === 'slim')  idx = Math.max(idx - 1, 0);

    return SIZES[idx];
  }, [height, weight, fit]);

  return (
    <div className="sizecalc">
      <div className="sizecalc__head">
        <div className="section__eyebrow">CALCULADORA</div>
        <h3 className="sizecalc__title">¿Qué talla pido?</h3>
      </div>
      <div className="sizecalc__body">
        <div className="sizecalc__controls">
          <label className="sizecalc__row">
            <span>Altura (cm)</span>
            <input type="range" min="150" max="210" value={height} onChange={(e) => setHeight(+e.target.value)} />
            <output>{height}</output>
          </label>
          <label className="sizecalc__row">
            <span>Peso (kg)</span>
            <input type="range" min="45" max="140" value={weight} onChange={(e) => setWeight(+e.target.value)} />
            <output>{weight}</output>
          </label>
          <div className="sizecalc__fit">
            <span>Cómo te gusta</span>
            <div className="seg">
              {['slim', 'regular', 'baggy'].map((f) => (
                <button key={f} className={`seg__btn ${fit === f ? 'seg__btn--on' : ''}`} onClick={() => setFit(f)}>{f.charAt(0).toUpperCase() + f.slice(1)}</button>
              ))}
            </div>
          </div>
        </div>
        <div className="sizecalc__result">
          <div className="sizecalc__resultLbl">Tu talla TRENT</div>
          <div className="sizecalc__resultVal">{size}</div>
          <div className="sizecalc__hint">
            Si dudas entre dos tallas, pilla la más grande.<br/>
            Consulta la guía de medidas en cada prenda.
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   GUIDES
   ============================================================ */
function renderText(text, boldWordsList) {
  const escaped = boldWordsList.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const boldPattern = new RegExp(`(${[...escaped, '__[^_]+__', '\\*\\*[^*]+\\*\\*'].join('|')})`, 'g');
  const parts = text.split(boldPattern);
  return parts.map((p, i) => {
    if (boldWordsList.includes(p)) return React.createElement('strong', {key: i}, p);
    if (p.startsWith('__') && p.endsWith('__')) return React.createElement('u', {key: i}, p.slice(2, -2));
    if (p.startsWith('**') && p.endsWith('**')) return React.createElement('strong', {key: i}, p.slice(2, -2));
    return p;
  });
}

function GuideModal({ guide, onClose }) {
  React.useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="guide-modal__overlay" onClick={onClose}>
      <div className="guide-modal" onClick={(e) => e.stopPropagation()}>
        <div className="guide-modal__tag">{guide.tag}</div>
        <h2 className="guide-modal__title">{guide.title}</h2>
        <p className="guide-modal__read">{guide.read} lectura</p>
        <div className="guide-modal__body">{guide.body.split('\n\n').map((para, i) => {
          const lines = para.split('\n');
          const firstLine = lines[0];
          const isHeading = firstLine.startsWith('¿') || /^[✅⚠️🤝]/.test(firstLine) === false && /^[A-ZÁÉÍÓÚ][^a-záéíóú]{2,}/.test(firstLine);
          const BW = (t) => renderText(t, ['Yepexpress', 'Hacoo', 'TRENT14']);
          if (isHeading && lines.length > 1) {
            return (
              <div key={i} style={{marginBottom: '16px'}}>
                <p style={{fontWeight: '700', fontSize: '15px', marginBottom: '4px'}}>{BW(firstLine)}</p>
                <p style={{whiteSpace: 'pre-line'}}>{BW(lines.slice(1).join('\n'))}</p>
              </div>
            );
          }
          return <p key={i} style={{marginBottom: '14px', whiteSpace: 'pre-line', fontWeight: isHeading ? '700' : undefined}}>{BW(para)}</p>;
        })}</div>
        <button className="guide-modal__close" onClick={onClose} aria-label="Cerrar">✕</button>
      </div>
    </div>
  );
}

function Guides() {
  const guides = window.TRENT_DATA.guides;
  const [active, setActive] = React.useState(null);

  return (
    <section id="guides" className="section section--guides">
      <div className="section__head">
        <div className="section__eyebrow">[ 04 ] GUÍAS</div>
        <h2 className="section__title">Lo que <em>nadie te cuenta</em>.</h2>
        <p className="section__lead">Tallas, aduanas, incidencias… las preguntas que te hacen dudar antes de pedir.</p>
      </div>

      <div className="guides__grid">
        {guides.map((g, i) => (
          <a key={i} href="#" className={`guide ${g.big ? 'guide--big' : ''}`}
            onClick={(e) => { 
              e.preventDefault(); 
              if (g.tag === 'MARCAS') {
                document.getElementById('drops')?.scrollIntoView && window.scrollTo({ top: document.getElementById('drops').offsetTop - 80, behavior: 'smooth' });
              } else if (g.body) {
                setActive(g);
              }
            }}>
            <div className="guide__tag">{g.tag}</div>
            <h3 className="guide__title">{g.title}</h3>
            <div className="guide__foot">
              <span className="guide__arrow">→</span>
            </div>
          </a>
        ))}
        <div className="guide guide--calc">
          <SizeCalculator />
        </div>
      </div>

      {active && <GuideModal guide={active} onClose={() => setActive(null)} />}
    </section>
  );
}

/* ============================================================
   FAQ
   ============================================================ */
function FAQ() {
  const { editMode, cfg, onSave } = React.useContext(window.EditCtx);
  const E = window.EditableText;
  const [open, setOpen] = useState(0);

  const faqs = [
    { qKey: 'faq0q', aKey: 'faq0a' },
    { qKey: 'faq1q', aKey: 'faq1a' },
    { qKey: 'faq2q', aKey: 'faq2a' },
    { qKey: 'faq3q', aKey: 'faq3a' },
    { qKey: 'faq4q', aKey: 'faq4a' },
  ];

  return (
    <section id="faq" className="section section--faq">
      <div className="section__head">
        <div className="section__eyebrow">[ 05 ] FAQ</div>
        <h2 className="section__title">Las preguntas <em>de siempre</em>.</h2>
      </div>
      <div className="faq__list">
        {faqs.map((f, i) => (
          <div key={i} className={`faq__item ${open === i ? 'faq__item--open' : ''}`}>
            <button className="faq__q" onClick={() => setOpen(open === i ? -1 : i)}>
              <span className="faq__n">0{i + 1}</span>
              <E tag="span" className="faq__qt" value={cfg[f.qKey]} fieldKey={f.qKey} editMode={editMode} onSave={onSave} />
              <span className="faq__plus">{open === i ? '−' : '+'}</span>
            </button>
            <div className="faq__a">
              <E tag="p" value={cfg[f.aKey]} fieldKey={f.aKey} editMode={editMode} onSave={onSave} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ============================================================
   FOOTER
   ============================================================ */
function Footer() {
  const { editMode, cfg, onSave } = React.useContext(window.EditCtx);
  const E = window.EditableText;
  return (
    <footer className="footer">
      <div className="footer__top">
        <div className="footer__left">
          <div className="footer__cta">
            <E tag="div" className="footer__cta-line" value={cfg.footerCta1} fieldKey="footerCta1" editMode={editMode} onSave={onSave} />
            <E tag="div" className="footer__cta-line footer__cta-line--big" value={cfg.footerCta2} fieldKey="footerCta2" editMode={editMode} onSave={onSave} />
            <a href={cfg.telegramLink} target="_blank" rel="noreferrer" className="btn btn--primary btn--lg">Chat de Telegram →</a>
          </div>
        </div>
        <div className="footer__right">
          <div className="footer__col">
            <div className="footer__h">Encuéntrame</div>
            <a href="https://www.tiktok.com/@trent_wave" target="_blank" rel="noreferrer">TikTok</a>
            <a href="https://t.me/trentthacoo" target="_blank" rel="noreferrer">Telegram</a>
          </div>
          <div className="footer__col">
            <div className="footer__h">Web</div>
            <a href="#how">Cómo comprar</a>
            <a href="#drops">Catálogo</a>
            <a href="#guides">Guías</a>
            <a href="#faq">FAQ</a>
          </div>
        </div>
      </div>
      <div className="footer__bottom">
        <div>© 2025 TRENT</div>
      </div>
    </footer>
  );
}

Object.assign(window, {
  Navbar, Hero, HowToBuy, Catalog, TelegramBlock, Guides, FAQ, Footer, Marquee, ProductPlaceholder, DiscountBar
});
