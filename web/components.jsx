// TRENT — componentes de secciones
// Usa window.TRENT_DATA y los Tweak* del panel global

const { useState, useEffect, useMemo, useRef } = React;

/* ============================================================
   DISCOUNT BAR — barra anuncio con código
   ============================================================ */
function DiscountBar() {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    try { navigator.clipboard.writeText('TRENT14'); } catch {}
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div className="discountbar">
      <div className="discountbar__inner">
        <span className="discountbar__gift">🎁</span>
        <span className="discountbar__msg">
          <strong>−14%</strong> en tu 1ª compra — código
        </span>
        <button className="discountbar__code" onClick={copy} title="Copiar código">
          <span className="discountbar__code-text">TRENT14</span>
          <span className="discountbar__code-copy">{copied ? '✓ copiado' : 'copiar'}</span>
        </button>
        <span className="discountbar__msg discountbar__msg--right">envío 7–15 días</span>
      </div>
    </div>
  );
}

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
        <li><a href="#how" onClick={(e) => { e.preventDefault(); onScrollTo('how'); }}>Cómo comprar</a></li>
        <li><a href="#drops" onClick={(e) => { e.preventDefault(); onScrollTo('drops'); }}>Links</a></li>
        <li><a href="#telegram" onClick={(e) => { e.preventDefault(); onScrollTo('telegram'); }}>Telegram</a></li>
        <li><a href="#guides" onClick={(e) => { e.preventDefault(); onScrollTo('guides'); }}>Guías</a></li>
        <li><a href="#faq" onClick={(e) => { e.preventDefault(); onScrollTo('faq'); }}>FAQ</a></li>
      </ul>
      <a href="https://t.me/trentthacoo" target="_blank" rel="noreferrer" className="btn btn--primary nav__cta">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>
        Entrar al canal
      </a>
    </nav>
  );
}

/* ============================================================
   HERO
   ============================================================ */
function Hero({ heroCopy, onScrollTo, palette }) {
  return (
    <header id="top" className="hero">
      <div className="hero__grid">
        <div className="hero__left">
          <div className="hero__eyebrow">
            <span className="dot dot--live"></span>
            Drops nuevos cada día · Código bienvenida −14%
          </div>
          <h1 className="hero__title">
            <span className="hero__title-line">VISTE</span>
            <span className="hero__title-line hero__title-line--accent">DIFERENTE.</span>
            <span className="hero__title-line">PAGA</span>
            <span className="hero__title-line hero__title-line--outline">MENOS.</span>
          </h1>
          <p className="hero__sub">{heroCopy}</p>
          <div className="hero__ctas">
            <a href="https://t.me/trentthacoo" target="_blank" rel="noreferrer" className="btn btn--primary btn--lg">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>
              Ver catálogo en Telegram
            </a>
            <button className="btn btn--ghost btn--lg" onClick={() => onScrollTo('how')}>
              Cómo funciona
              <span className="btn__arrow">→</span>
            </button>
          </div>
          <div className="hero__metrics">
            <div className="metric">
              <div className="metric__num">+340</div>
              <div className="metric__lbl">Prendas activas</div>
            </div>
            <div className="metric metric--accent">
              <div className="metric__num">−14%</div>
              <div className="metric__lbl">1ª compra · TRENT14</div>
            </div>
            <div className="metric">
              <div className="metric__num">7–15<span style={{ fontSize: '0.5em' }}>d</span></div>
              <div className="metric__lbl">Entrega media</div>
            </div>
          </div>
        </div>

        <aside className="hero__right">
          <div className="hero__card hero__card--big">
            <div className="hero__card-label">— ÚLTIMO DROP</div>
            <div className="hero__product">
              <ProductPlaceholder stripe={palette.primary} bg={palette.bgSoft} label="hoodie boxy" drop="NEW" />
            </div>
            <div className="hero__product-meta">
              <div>
                <div className="hero__product-name">Hoodie Boxy Cream</div>
                <div className="hero__product-cat">Sudaderas · TRENT</div>
              </div>
              <div className="hero__product-price">12,40€</div>
            </div>
          </div>

          <div className="hero__card hero__card--code">
            <div className="hero__card-label">— CÓDIGO BIENVENIDA</div>
            <div className="hero__code-row">
              <span className="hero__code-gift">🎁</span>
              <div className="hero__code-stack">
                <div className="hero__code-val">TRENT14</div>
                <div className="hero__code-sub">−14% en tu 1ª compra</div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </header>
  );
}

/* ============================================================
   STEPS — Cómo comprar
   ============================================================ */
function HowToBuy() {
  const steps = window.TRENT_DATA.steps;
  return (
    <section id="how" className="section section--how">
      <div className="section__head">
        <div className="section__eyebrow">[ 01 ] PROCESO</div>
        <h2 className="section__title">Cómprate todo en <em>4 pasos</em>.</h2>
        <p className="section__lead">Pulsa cada paso y te lleva directo. Si es tu primera vez, tarda un café. Después, 30 segundos.</p>
      </div>
      <ol className="steps">
        {steps.map((s) => (
          <li key={s.n} className="step">
            <a
              className="step__link"
              href={s.href}
              target="_blank"
              rel="noreferrer"
            >
              <div className="step__n">{s.n}</div>
              <div className="step__body">
                <h3 className="step__title">{s.title}</h3>
                <p className="step__desc">{s.body}</p>
                <div className="step__foot">
                  <span className="step__tag">{s.tag}</span>
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
function Catalog({ density, palette }) {
  const staticProducts = window.TRENT_DATA.products;
  const [botProducts, setBotProducts] = useState([]);
  const categories = window.TRENT_DATA.categories;
  const brands = window.TRENT_DATA.brands;
  const itemsPerPage = density === 'compact' ? 20 : density === 'comfy' ? 12 : 16;

  useEffect(() => {
    const db = window._firebaseDB;
    if (!db) return;
    const unsub = db.collection('products').orderBy('data', 'desc').onSnapshot((snap) => {
      setBotProducts(snap.docs.map((doc) => {
        const d = doc.data();
        return {
          id: 'fb-' + doc.id,
          name: d.nom || '',
          cat: 'Hacoo',
          brand: d.marca || 'Hacoo',
          price: d.preu || '',
          colors: d.colors || '',
          hot: true,
          drop: 'NEW',
          stripe: '#1E3FBE',
          bg: '#ECECEC',
          image: d.imatge || '',
          url: d.link_afiliats || '',
        };
      }));
    }, () => {});
    return () => unsub();
  }, []);

  const products = [...botProducts, ...staticProducts];

  const [cat, setCat] = useState('Todo');
  const [brand, setBrand] = useState('Todas');
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [wishlist, setWishlist] = useState(() => {
    try { return JSON.parse(localStorage.getItem('trent_wishlist') || '[]'); } catch { return []; }
  });
  const [toast, setToast] = useState(null);

  useEffect(() => {
    localStorage.setItem('trent_wishlist', JSON.stringify(wishlist));
  }, [wishlist]);

  const filtered = useMemo(() => {
    return products.filter((p) => {
      if (cat !== 'Todo' && p.cat !== cat) return false;
      if (brand !== 'Todas' && p.brand !== brand) return false;
      if (q && !p.name.toLowerCase().includes(q.toLowerCase())) return false;
      return true;
    });
  }, [products, cat, brand, q]);

  const totalPages = Math.ceil(filtered.length / itemsPerPage);
  const paginated = filtered.slice((page - 1) * itemsPerPage, page * itemsPerPage);

  const toggleWish = (id) => {
    setWishlist((w) => w.includes(id) ? w.filter((x) => x !== id) : [...w, id]);
  };

  const copyLink = (p) => {
    const link = p.url || `https://t.me/trentthacoo/${p.id}`;
    try { navigator.clipboard.writeText(link); } catch {}
    setToast(`Link copiado · ${p.name}`);
    setTimeout(() => setToast(null), 1800);
  };

  const resetPagination = () => setPage(1);

  return (
    <section id="drops" className={`section section--catalog density--${density}`}>
      <div className="section__head section__head--row">
        <div>
          <div className="section__eyebrow">[ 02 ] CATÁLOGO</div>
          <h2 className="section__title">Prendas <em>seleccionadas</em>.</h2>
          <p className="section__lead">{filtered.length} prendas disponibles. Filtra por categoría y marca o busca por nombre.</p>
        </div>
        <div className="catalog__search">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.5" y2="16.5"/></svg>
          <input placeholder="Busca hoodie, sneaker…" value={q} onChange={(e) => { setQ(e.target.value); resetPagination(); }} />
          {q && <button className="catalog__clear" onClick={() => { setQ(''); resetPagination(); }}>×</button>}
        </div>
      </div>

      <div className="catalog__filters">
        <div className="filter-group">
          <span className="filter-label">Categoría</span>
          <div className="chips">
            {categories.map((c) => (
              <button key={c} className={`chip ${cat === c ? 'chip--active' : ''}`} onClick={() => { setCat(c); resetPagination(); }}>
                {c}
              </button>
            ))}
          </div>
        </div>
        <div className="filter-group">
          <span className="filter-label">Marca</span>
          <div className="chips">
            {brands.map((b) => (
              <button key={b} className={`chip ${brand === b ? 'chip--active' : ''}`} onClick={() => { setBrand(b); resetPagination(); }}>
                {b}
              </button>
            ))}
          </div>
        </div>
      </div>

      {wishlist.length > 0 && (
        <button className="wishlist-badge" onClick={() => setWishlist([])}>
          ♥ {wishlist.length} en wishlist · borrar
        </button>
      )}

      <div className="grid">
        {paginated.map((p) => (
          <article key={p.id} className={`card ${p.hot ? 'card--hot' : ''}`}>
            <div className="card__img">
              {p.image
                ? <img src={p.image} alt={p.name} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top center', display: 'block' }} />
                : <ProductPlaceholder stripe={p.stripe} bg={p.bg} label={p.name} drop={p.drop} />
              }
              <button
                className={`card__wish ${wishlist.includes(p.id) ? 'card__wish--on' : ''}`}
                onClick={() => toggleWish(p.id)}
                aria-label="Guardar"
              >
                {wishlist.includes(p.id) ? '♥' : '♡'}
              </button>
            </div>
            <div className="card__body">
              <div className="card__row">
                <div className="card__cat">{p.brand}</div>
                <div className="card__price">{p.price}</div>
              </div>
              <h3 className="card__name">{p.name}</h3>
              <div className="card__sub">{p.colors ? `${p.colors} colores 🎨` : p.cat}</div>
              <div className="card__actions">
                <a href={p.url || 'https://t.me/trentthacoo'} target="_blank" rel="noreferrer" className="card__btn card__btn--primary">
                  Comprar →
                </a>
                <button className="card__btn card__btn--ghost" onClick={() => copyLink(p)} title="Copiar link">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                </button>
              </div>
            </div>
          </article>
        ))}
        {filtered.length === 0 && (
          <div className="empty">
            <div className="empty__big">Sin resultados</div>
            <div className="empty__sub">Intenta con otro filtro o búsqueda.</div>
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
    </section>
  );
}

/* ============================================================
   TELEGRAM block
   ============================================================ */
function TelegramBlock() {
  const benefits = [
    { ic: '📌', t: 'Links organizados por categoría', s: 'Sneakers, hoodies, cargos… cada uno con su carpeta. Sin scroll infinito.' },
    { ic: '⚡', t: 'Drops en directo', s: 'Cuando encuentro algo bueno, te llega al móvil. Lo pillas antes que nadie.' },
    { ic: '🛟', t: 'Soporte 1 a 1', s: '¿Dudas de talla o incidencia? Me escribes y te ayudo personalmente.' },
    { ic: '🔓', t: 'Gratis y sin spam', s: 'Solo subo cuando vale la pena. Cero publi de relleno.' },
  ];

  return (
    <section id="telegram" className="section section--telegram">
      <div className="telegram__inner">
        <div className="telegram__left">
          <div className="section__eyebrow section__eyebrow--light">[ 03 ] EL CANAL</div>
          <h2 className="section__title section__title--light">
            Mi Telegram es donde <em>vive todo</em>.
          </h2>
          <p className="section__lead section__lead--light">
            Es el canal donde publicó cada día los enlaces directos a las prendas. De la inspiración a tu carrito en 1 toque.
          </p>
          <a href="https://t.me/trentthacoo" target="_blank" rel="noreferrer" className="btn btn--invert btn--lg">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>
            t.me/trentthacoo
          </a>
          <div className="telegram__handle">12.4k miembros · activos hoy</div>
        </div>
        <div className="telegram__right">
          {benefits.map((b, i) => (
            <div key={i} className="benefit">
              <div className="benefit__ic">{b.ic}</div>
              <div>
                <div className="benefit__t">{b.t}</div>
                <div className="benefit__s">{b.s}</div>
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
  const [chest, setChest] = useState(94);
  const [waist, setWaist] = useState(80);
  const [fit, setFit] = useState('regular');

  const size = useMemo(() => {
    let base = chest;
    if (fit === 'baggy') base -= 6;
    if (fit === 'slim') base += 4;
    if (base < 88) return 'S';
    if (base < 96) return 'M';
    if (base < 104) return 'L';
    if (base < 112) return 'XL';
    return 'XXL';
  }, [chest, fit]);

  return (
    <div className="sizecalc">
      <div className="sizecalc__head">
        <div className="section__eyebrow">CALCULADORA</div>
        <h3 className="sizecalc__title">¿Qué talla pido?</h3>
      </div>
      <div className="sizecalc__body">
        <div className="sizecalc__controls">
          <label className="sizecalc__row">
            <span>Pecho (cm)</span>
            <input type="range" min="78" max="124" value={chest} onChange={(e) => setChest(+e.target.value)} />
            <output>{chest}</output>
          </label>
          <label className="sizecalc__row">
            <span>Cintura (cm)</span>
            <input type="range" min="64" max="120" value={waist} onChange={(e) => setWaist(+e.target.value)} />
            <output>{waist}</output>
          </label>
          <div className="sizecalc__fit">
            <span>Cómo te gusta</span>
            <div className="seg">
              {['slim', 'regular', 'baggy'].map((f) => (
                <button key={f} className={`seg__btn ${fit === f ? 'seg__btn--on' : ''}`} onClick={() => setFit(f)}>{f}</button>
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
function Guides() {
  const guides = window.TRENT_DATA.guides;
  return (
    <section id="guides" className="section section--guides">
      <div className="section__head">
        <div className="section__eyebrow">[ 04 ] GUÍAS</div>
        <h2 className="section__title">Lo que <em>nadie te cuenta</em>.</h2>
        <p className="section__lead">Tallas, aduanas, incidencias… las preguntas que te hacen dudar antes de pedir.</p>
      </div>

      <div className="guides__grid">
        {guides.map((g, i) => (
          <a key={i} href="#" className={`guide ${g.big ? 'guide--big' : ''}`}>
            <div className="guide__tag">{g.tag}</div>
            <h3 className="guide__title">{g.title}</h3>
            <div className="guide__foot">
              <span>{g.read} lectura</span>
              <span className="guide__arrow">→</span>
            </div>
          </a>
        ))}
        <div className="guide guide--calc">
          <SizeCalculator />
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   FAQ
   ============================================================ */
function FAQ() {
  const faqs = window.TRENT_DATA.faq;
  const [open, setOpen] = useState(0);
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
              <span className="faq__qt">{f.q}</span>
              <span className="faq__plus">{open === i ? '−' : '+'}</span>
            </button>
            <div className="faq__a">
              <p>{f.a}</p>
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
  return (
    <footer className="footer">
      <div className="footer__top">
        <div className="footer__logo">
          <img src={(window.__resources && window.__resources.trentLogo) || "assets/trent-logo.png"} alt="TRENT Clothing" />
        </div>
        <div className="footer__cta">
          <div className="footer__cta-line">¿Listo para</div>
          <div className="footer__cta-line footer__cta-line--big">PILLAR DROPS?</div>
          <a href="https://t.me/trentthacoo" target="_blank" rel="noreferrer" className="btn btn--primary btn--lg">Entrar al Telegram →</a>
        </div>
      </div>
      <div className="footer__cols">
        <div className="footer__col">
          <div className="footer__h">Encuéntrame</div>
          <a href="https://www.tiktok.com/@trent_wave" target="_blank" rel="noreferrer">TikTok · @trent_wave</a>
          <a href="https://t.me/trentthacoo" target="_blank" rel="noreferrer">Telegram · trentthacoo</a>
          <a href="#">Instagram · pronto</a>
          <a href="mailto:hola@trentclothing.com">hola@trentclothing.com</a>
        </div>
        <div className="footer__col">
          <div className="footer__h">Web</div>
          <a href="#how">Cómo comprar</a>
          <a href="#drops">Catálogo</a>
          <a href="#guides">Guías</a>
          <a href="#faq">FAQ</a>
        </div>
        <div className="footer__col">
          <div className="footer__h">Legal</div>
          <a href="#">Aviso de afiliación</a>
          <a href="#">Política de cookies</a>
          <a href="#">Términos</a>
        </div>
      </div>
      <div className="footer__bottom">
        <div>© 2026 TRENT Clothing — Curaduría no oficial de Hacoo.</div>
        <div>Hecho con ☕ y mucho scroll.</div>
      </div>
    </footer>
  );
}

Object.assign(window, {
  Navbar, Hero, HowToBuy, Catalog, TelegramBlock, Guides, FAQ, Footer, Marquee, ProductPlaceholder, DiscountBar
});
