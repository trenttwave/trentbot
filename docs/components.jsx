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
function Hero({ onScrollTo, palette }) {
  const { editMode, cfg, onSave } = React.useContext(window.EditCtx);
  const E = window.EditableText;
  return (
    <header id="top" className="hero">
      <div className="hero__grid">
        <div className="hero__left">
          <div className="hero__eyebrow">
            <span className="dot dot--live"></span>
            <E tag="span" value={cfg.heroEyebrow} fieldKey="heroEyebrow" editMode={editMode} onSave={onSave} />
          </div>
          <h1 className="hero__title">
            <span className="hero__title-line">VISTE</span>
            <span className="hero__title-line hero__title-line--accent">DIFERENTE.</span>
            <span className="hero__title-line">PAGA</span>
            <span className="hero__title-line hero__title-line--outline">MENOS.</span>
          </h1>
          <E tag="p" className="hero__sub" value={cfg.heroCopy} fieldKey="heroCopy" editMode={editMode} onSave={onSave} />
          <div className="hero__ctas">
            <a href={cfg.telegramLink} target="_blank" rel="noreferrer" className="btn btn--primary btn--lg">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>
              <E tag="span" value={cfg.heroBtnPrimary} fieldKey="heroBtnPrimary" editMode={editMode} onSave={onSave} />
            </a>
            <button className="btn btn--ghost btn--lg" onClick={() => onScrollTo('how')}>
              <E tag="span" value={cfg.heroBtnSecondary} fieldKey="heroBtnSecondary" editMode={editMode} onSave={onSave} />
              <span className="btn__arrow">→</span>
            </button>
          </div>
          <div className="hero__metrics">
            <div className="metric">
              <E className="metric__num" value={cfg.metric1Num} fieldKey="metric1Num" editMode={editMode} onSave={onSave} />
              <E className="metric__lbl" value={cfg.metric1Lbl} fieldKey="metric1Lbl" editMode={editMode} onSave={onSave} />
            </div>
            <div className="metric metric--accent">
              <E className="metric__num" value={cfg.metric2Num} fieldKey="metric2Num" editMode={editMode} onSave={onSave} />
              <E className="metric__lbl" value={cfg.metric2Lbl} fieldKey="metric2Lbl" editMode={editMode} onSave={onSave} />
            </div>
            <div className="metric">
              <E className="metric__num" value={cfg.metric3Num} fieldKey="metric3Num" editMode={editMode} onSave={onSave} />
              <E className="metric__lbl" value={cfg.metric3Lbl} fieldKey="metric3Lbl" editMode={editMode} onSave={onSave} />
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
                <E className="hero__product-name" value={cfg.heroCardName} fieldKey="heroCardName" editMode={editMode} onSave={onSave} />
                <E className="hero__product-cat" value={cfg.heroCardCat} fieldKey="heroCardCat" editMode={editMode} onSave={onSave} />
              </div>
              <E className="hero__product-price" value={cfg.heroCardPrice} fieldKey="heroCardPrice" editMode={editMode} onSave={onSave} />
            </div>
          </div>

          <div className="hero__card hero__card--code">
            <div className="hero__card-label">— CÓDIGO BIENVENIDA</div>
            <div className="hero__code-row">
              <span className="hero__code-gift">🎁</span>
              <div className="hero__code-stack">
                <E className="hero__code-val" value={cfg.discountCode} fieldKey="discountCode" editMode={editMode} onSave={onSave} />
                <E className="hero__code-sub" value={`−${cfg.discountPct}% en tu 1ª compra`} fieldKey="discountPct" editMode={editMode} onSave={onSave} />
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
        <div className="section__eyebrow">[ 01 ] PROCESO</div>
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
// Detecta categoría desde el nombre del producto
function detectCat(name, savedCat) {
  if (savedCat) return savedCat;
  // Normalize accents: á→a, é→e, í→i, ó→o, ú→u
  const n = (name || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  if (/zapati|sneaker|zapatill|boot|bota|shoe|calzad/.test(n)) return 'Zapatos';
  if (/camiseta|tee|tshirt|polo|shirt|camisa|top\b/.test(n)) return 'Camisetas';
  if (/hoodie|sudadera|sweat|jersey|crewneck/.test(n)) return 'Sudaderas';
  if (/pantalon|jean|denim|cargo|jogger|short|bermuda|vaquero/.test(n)) return 'Pantalones';
  if (/chaqueta|jacket|abrigo|coat|puffer|parka|blazer|chaleco/.test(n)) return 'Chaquetas';
  if (/bolso|bag|mochila|tote|clutch|cartera/.test(n)) return 'Bolsos';
  if (/vestido|dress|falda|skirt/.test(n)) return 'Vestidos';
  if (/gorro|hat|cap|gorra|beanie|bucket|scrunchie/.test(n)) return 'Accesorios';
  if (/cinturon|belt|collar|pulsera|anillo|ring|joya|jewel|bufanda|scarf/.test(n)) return 'Accesorios';
  return 'Otros';
}

function Catalog({ density, palette }) {
  const ctx = React.useContext(window.EditCtx || React.createContext({ editMode: false, cfg: {}, onSave: () => {} }));
  const editMode = ctx ? ctx.editMode : false;
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const itemsPerPage = density === 'compact' ? 20 : density === 'comfy' ? 12 : 16;

  const [cat, setCat] = useState('Todo');
  const [brand, setBrand] = useState('Todas');
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [filterOpen, setFilterOpen] = useState(false);
  const [wishlist, setWishlist] = useState(() => {
    try { return JSON.parse(localStorage.getItem('trent_wishlist') || '[]'); } catch { return []; }
  });
  const [toast, setToast] = useState(null);

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
  }, [wishlist]);

  const brands = useMemo(() => {
    const set = new Set(products.map(p => p.marca || p.brand || '').filter(Boolean));
    return ['Todas', ...Array.from(set).sort()];
  }, [products]);

  const cats = useMemo(() => {
    const set = new Set(products.map(p => detectCat(p.nom || p.name || '', p.categoria)));
    return ['Todo', ...Array.from(set).sort()];
  }, [products]);

  const filtered = useMemo(() => {
    return products.filter((p) => {
      const name = p.nom || p.name || '';
      const brandVal = p.marca || p.brand || '';
      if (brand !== 'Todas' && brandVal !== brand) return false;
      if (cat !== 'Todo' && detectCat(name, p.categoria) !== cat) return false;
      if (q && !name.toLowerCase().includes(q.toLowerCase())) return false;
      return true;
    });
  }, [products, brand, cat, q]);

  const totalPages = Math.ceil(filtered.length / itemsPerPage);
  const paginated = filtered.slice((page - 1) * itemsPerPage, page * itemsPerPage);

  const toggleWish = (id) => {
    setWishlist((w) => w.includes(id) ? w.filter((x) => x !== id) : [...w, id]);
  };

  const resetPagination = () => setPage(1);

  const activeFilters = (brand !== 'Todas' ? 1 : 0) + (cat !== 'Todo' ? 1 : 0);

  const clearFilters = () => { setBrand('Todas'); setCat('Todo'); resetPagination(); };

  return (
    <section id="drops" className={`section section--catalog density--${density}`}>
      <div className="section__head">
        <div className="section__eyebrow">[ 02 ] CATÁLOGO</div>
        <h2 className="section__title">Prendas <em>seleccionadas</em>.</h2>
        <p className="section__lead">{loading ? 'Cargando…' : `${filtered.length} prendas disponibles. Filtra por marca o en el buscador.`}</p>
      </div>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 20 }}>
        <div className="catalog__search" style={{ flex: 1, minWidth: 350 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.5" y2="16.5"/></svg>
          <input placeholder="Busca hoodie, sneaker…" value={q} onChange={(e) => { setQ(e.target.value); resetPagination(); }} />
          {q && <button className="catalog__clear" onClick={() => { setQ(''); resetPagination(); }}>×</button>}
        </div>
        <button onClick={() => setFilterOpen(o => !o)} style={{
          display: 'flex', alignItems: 'center', gap: 6, padding: '12px 18px',
          border: `2px solid var(--c-primary)`,
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
      )}

      {wishlist.length > 0 && (
        <button className="wishlist-badge" onClick={() => setWishlist([])}>
          ♥ {wishlist.length} en wishlist · borrar
        </button>
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
          const link = p.link_afiliats || p.link || 'https://t.me/trentthacoo';

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
              <div className="card__img" style={{ position: 'relative' }}>
                {imgUrl
                  ? <img src={imgUrl} alt={name} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                  : <ProductPlaceholder stripe="#1E3FBE" bg="#ECECEC" label={name} />
                }
                {editMode && (
                  <button onClick={changeImage} style={{
                    position: 'absolute', inset: 0, width: '100%', height: '100%',
                    background: 'rgba(30,63,190,.55)', color: '#fff', border: 'none',
                    cursor: 'pointer', fontFamily: 'inherit', fontSize: 13, fontWeight: 600,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                  }}>
                    🖼️ Cambiar foto
                  </button>
                )}
                {!editMode && (
                  <button
                    className={`card__wish ${wishlist.includes(p.id) ? 'card__wish--on' : ''}`}
                    onClick={() => toggleWish(p.id)}
                    aria-label="Guardar"
                  >
                    {wishlist.includes(p.id) ? '♥' : '♡'}
                  </button>
                )}
              </div>
              <div className="card__body">
                <div className="card__row">
                  {editMode
                    ? <span contentEditable suppressContentEditableWarning
                        style={{ outline: '2px dashed #1E3FBE', borderRadius: 4, padding: '1px 4px', minWidth: 10 }}
                        onBlur={e => saveProduct('marca', e.currentTarget.textContent.trim())}
                      >{brand}</span>
                    : <div className="card__cat">{brand}</div>
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
                  : <h3 className="card__name">{name}</h3>
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
            <div key={i} className="benefit">
              <div className="benefit__head">
                <div className="benefit__ic">{b.ic}</div>
                <E className="benefit__t" value={cfg[b.tKey]} fieldKey={b.tKey} editMode={editMode} onSave={onSave} />
              </div>
              <E className="benefit__s" value={cfg[b.sKey]} fieldKey={b.sKey} editMode={editMode} onSave={onSave} />
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
