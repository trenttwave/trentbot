// TRENT — datos de muestra (productos, guías, FAQ)

window.TRENT_DATA = {
  products: [
    // Sneakers
    { id: 'p01', name: 'Chunky Sneaker Y2K', cat: 'Sneakers', brand: 'Adidas', price: '24,80 €', hot: true, drop: 'NEW', stripe: '#1E3FBE', bg: '#ECECEC' },
    { id: 'p02', name: 'Skate Sneaker Suede', cat: 'Sneakers', brand: 'Nike', price: '19,60 €', hot: false, drop: '', stripe: '#1E3FBE', bg: '#E4E4E4' },
    { id: 'p03', name: 'Runner Low Classic', cat: 'Sneakers', brand: 'Puma', price: '18,90 €', hot: true, drop: 'TOP', stripe: '#0A0A12', bg: '#DCDCDC' },
    { id: 'p04', name: 'Court Sneaker White', cat: 'Sneakers', brand: 'Adidas', price: '21,30 €', hot: false, drop: '', stripe: '#1E3FBE', bg: '#ECECEC' },
    { id: 'p05', name: 'Basketball Hoop', cat: 'Sneakers', brand: 'Nike', price: '26,50 €', hot: true, drop: 'NEW', stripe: '#0A0A12', bg: '#E4E4E4' },
    { id: 'p06', name: 'Retro Runner Mesh', cat: 'Sneakers', brand: 'Puma', price: '17,20 €', hot: false, drop: '', stripe: '#1E3FBE', bg: '#DCDCDC' },
    // Sudaderas
    { id: 'p07', name: 'Hoodie Boxy Cream', cat: 'Sudaderas', brand: 'TRENT', price: '12,40 €', hot: true, drop: 'NEW', stripe: '#1E3FBE', bg: '#ECECEC' },
    { id: 'p08', name: 'Zip Hoodie Half', cat: 'Sudaderas', brand: 'Stüssy', price: '15,60 €', hot: false, drop: '', stripe: '#0A0A12', bg: '#DCDCDC' },
    { id: 'p09', name: 'Crewneck Heavy 400g', cat: 'Sudaderas', brand: 'Carhartt', price: '13,20 €', hot: false, drop: '', stripe: '#1E3FBE', bg: '#E4E4E4' },
    { id: 'p10', name: 'Oversized Hoodie Washed', cat: 'Sudaderas', brand: 'TRENT', price: '14,80 €', hot: true, drop: '', stripe: '#0A0A12', bg: '#ECECEC' },
    // Camisetas
    { id: 'p11', name: 'Tee Oversize Logo', cat: 'Camisetas', brand: 'TRENT', price: '6,80 €', hot: false, drop: '', stripe: '#1E3FBE', bg: '#DCDCDC' },
    { id: 'p12', name: 'Graphic Tee Print', cat: 'Camisetas', brand: 'Stüssy', price: '7,50 €', hot: false, drop: '', stripe: '#1E3FBE', bg: '#ECECEC' },
    { id: 'p13', name: 'Boxy Tee Basic', cat: 'Camisetas', brand: 'TRENT', price: '5,90 €', hot: true, drop: 'TOP', stripe: '#0A0A12', bg: '#E4E4E4' },
    { id: 'p14', name: 'Retro Logo Tee', cat: 'Camisetas', brand: 'Carhartt', price: '8,20 €', hot: false, drop: '', stripe: '#1E3FBE', bg: '#DCDCDC' },
    // Pantalones
    { id: 'p15', name: 'Cargo Pant Wide', cat: 'Pantalones', brand: 'TRENT', price: '14,20 €', hot: false, drop: '', stripe: '#1E3FBE', bg: '#E4E4E4' },
    { id: 'p16', name: 'Denim Baggy Washed', cat: 'Pantalones', brand: 'Carhartt', price: '17,40 €', hot: false, drop: '', stripe: '#1E3FBE', bg: '#DCDCDC' },
    { id: 'p17', name: 'Straight Jeans Black', cat: 'Pantalones', brand: 'Stüssy', price: '16,10 €', hot: true, drop: 'NEW', stripe: '#0A0A12', bg: '#ECECEC' },
    // Chaquetas
    { id: 'p18', name: 'Puffer Jacket Tech', cat: 'Chaquetas', brand: 'Nike', price: '32,10 €', hot: true, drop: 'NEW', stripe: '#0A0A12', bg: '#ECECEC' },
    { id: 'p19', name: 'Varsity Jacket Wool', cat: 'Chaquetas', brand: 'Carhartt', price: '38,90 €', hot: true, drop: 'TOP', stripe: '#0A0A12', bg: '#E4E4E4' },
    { id: 'p20', name: 'Windbreaker Nylon', cat: 'Chaquetas', brand: 'Adidas', price: '28,50 €', hot: false, drop: '', stripe: '#1E3FBE', bg: '#DCDCDC' },
    // Bolsos
    { id: 'p21', name: 'Crossbody Mini Bag', cat: 'Bolsos', brand: 'TRENT', price: '9,30 €', hot: false, drop: '', stripe: '#0A0A12', bg: '#E4E4E4' },
    { id: 'p22', name: 'Tote Canvas Logo', cat: 'Bolsos', brand: 'Stüssy', price: '5,80 €', hot: false, drop: '', stripe: '#0A0A12', bg: '#DCDCDC' },
    { id: 'p23', name: 'Shoulder Bag Leather', cat: 'Bolsos', brand: 'Carhartt', price: '12,40 €', hot: true, drop: '', stripe: '#1E3FBE', bg: '#ECECEC' },
    // Accesorios
    { id: 'p24', name: 'Bucket Hat Nylon', cat: 'Accesorios', brand: 'TRENT', price: '4,90 €', hot: false, drop: '', stripe: '#0A0A12', bg: '#DCDCDC' },
    { id: 'p25', name: 'Beanie Knit Heavy', cat: 'Accesorios', brand: 'Stüssy', price: '3,90 €', hot: false, drop: '', stripe: '#0A0A12', bg: '#ECECEC' },
    { id: 'p26', name: 'Socks Pack x3', cat: 'Accesorios', brand: 'Nike', price: '6,20 €', hot: false, drop: '', stripe: '#1E3FBE', bg: '#E4E4E4' },
    // Más prendas para llegar a ~40
    { id: 'p27', name: 'Track Pants Velvet', cat: 'Pantalones', brand: 'TRENT', price: '13,70 €', hot: true, drop: 'NEW', stripe: '#0A0A12', bg: '#DCDCDC' },
    { id: 'p28', name: 'Polo Shirt Vintage', cat: 'Camisetas', brand: 'Adidas', price: '9,50 €', hot: false, drop: '', stripe: '#1E3FBE', bg: '#ECECEC' },
    { id: 'p29', name: 'Cargo Vest Tech', cat: 'Chaquetas', brand: 'Nike', price: '19,80 €', hot: true, drop: '', stripe: '#1E3FBE', bg: '#E4E4E4' },
    { id: 'p30', name: 'Running Shorts', cat: 'Pantalones', brand: 'Puma', price: '11,30 €', hot: false, drop: '', stripe: '#0A0A12', bg: '#DCDCDC' },
    { id: 'p31', name: 'Oversized Shirt', cat: 'Camisetas', brand: 'Stüssy', price: '10,60 €', hot: true, drop: 'TOP', stripe: '#1E3FBE', bg: '#ECECEC' },
    { id: 'p32', name: 'Combat Boots', cat: 'Sneakers', brand: 'Carhartt', price: '35,40 €', hot: true, drop: 'NEW', stripe: '#0A0A12', bg: '#E4E4E4' },
    { id: 'p33', name: 'Crossbody Bag Tech', cat: 'Bolsos', brand: 'Nike', price: '14,20 €', hot: false, drop: '', stripe: '#1E3FBE', bg: '#DCDCDC' },
    { id: 'p34', name: 'Joggers Fleece', cat: 'Pantalones', brand: 'Adidas', price: '12,90 €', hot: false, drop: '', stripe: '#0A0A12', bg: '#ECECEC' },
    { id: 'p35', name: 'Cap Baseball Logo', cat: 'Accesorios', brand: 'TRENT', price: '5,40 €', hot: true, drop: '', stripe: '#1E3FBE', bg: '#E4E4E4' },
    { id: 'p36', name: 'Swim Shorts Neon', cat: 'Pantalones', brand: 'Puma', price: '8,70 €', hot: false, drop: '', stripe: '#0A0A12', bg: '#DCDCDC' },
    { id: 'p37', name: 'Long Sleeve Tech', cat: 'Camisetas', brand: 'TRENT', price: '7,30 €', hot: false, drop: '', stripe: '#1E3FBE', bg: '#ECECEC' },
    { id: 'p38', name: 'Tracksuit Set 2pc', cat: 'Pantalones', brand: 'Carhartt', price: '22,60 €', hot: true, drop: 'TOP', stripe: '#0A0A12', bg: '#E4E4E4' },
    { id: 'p39', name: 'Leather Belt Gold', cat: 'Accesorios', brand: 'Stüssy', price: '6,80 €', hot: false, drop: '', stripe: '#1E3FBE', bg: '#DCDCDC' },
    { id: 'p40', name: 'Waterproof Jacket', cat: 'Chaquetas', brand: 'Nike', price: '31,20 €', hot: true, drop: 'NEW', stripe: '#1E3FBE', bg: '#ECECEC' },
  ],

  steps: [
    {
      n: '01',
      title: 'Descarga la app',
      body: 'Disponible en iOS y Android. Es donde compras todas tus prendas TRENT.',
      tag: 'iOS · Android',
      href: 'https://apps.apple.com',
      cta: 'Descargar →',
    },
    {
      n: '02',
      title: 'Únete a mi Telegram',
      body: 'El canal donde publico cada día los enlaces a las mejores prendas seleccionadas.',
      tag: '+12k miembros',
      href: 'https://t.me/trentthacoo',
      cta: 'Abrir canal →',
    },
    {
      n: '03',
      title: 'Encuentra tu prenda',
      body: 'Busca en nuestro catálogo o en el canal. Filtra por marca, categoría y precio.',
      tag: 'Búsqueda rápida',
      href: '#drops',
      cta: 'Ver catálogo →',
    },
    {
      n: '04',
      title: 'Usa TRENT14 y compra',
      body: 'En tu primera compra aplica el código TRENT14 para llevatelo con −14%.',
      tag: '−14% 1ª compra',
      href: 'https://apps.apple.com',
      cta: 'Comprar ahora →',
    },
  ],

  guides: [
    { tag: '🆕 NOVEDAD', title: 'HACOO vs YEPEXPRESS — ¿Cuál es la diferencia?', read: '3 min', big: true, body: '🤝 Yepexpress es una plataforma oficial creada por Hacoo. __Es decir, no son competidores — son la misma empresa, y trabajan juntas.__\n\n⚠️ Hace unos meses, Hacoo empezó a retirar ciertas marcas de su catálogo principal — Nike, New Balance y otras — probablemente por presión legal. Para no perder esos productos, crearon Yepexpress: una app paralela donde esos artículos siguen disponibles a través de links de Telegram.\n\n¿Cómo funciona la combinación? 🔗\nEl flujo es sencillo: encuentras el producto a través de un link (como los que publico en el canal), lo abres en Yepexpress y completas el pago ahí. No puedes buscar productos dentro de la app de Yepexpress — necesitas el link directo.\n\n¿Funcionan los dos con TRENT14? 🏷️\nSí. El código TRENT14 aplica un 14% de descuento en tu primera compra en ambas plataformas.\n\n✅ **Conclusión:** No tienes que elegir entre una u otra — las necesitas las dos. Hacoo para la mayoría de productos, Yepexpress para marcas como Nike o New Balance que ya no aparecen en Hacoo.' },
    { tag: 'TALLAS', title: 'Cómo elegir tu talla sin fallar', read: '4 min', big: true, body: 'Las tallas no siempre coinciden con las europeas — suelen ir más pequeñas. El truco es no fiarte de la S/M/L y mirar siempre la tabla de medidas en centímetros que aparece en cada producto. Mídete el pecho, la cintura y la cadera con una cinta métrica antes de pedir. Si dudas entre dos tallas, pide siempre la más grande.' },
    { tag: 'ENVÍO', title: 'Tiempos de envío y opciones', read: '3 min', body: 'El envío estándar tarda entre 7 y 15 días hábiles desde China. La mayoría de pedidos llegan en 10 días. No hay envío express disponible. El seguimiento llega por email una vez sale el paquete. Si no ves movimiento en 20 días, abre una incidencia en la app.' },
    { tag: 'CÓDIGO', title: 'Cómo usar TRENT14 — −14%', read: '2 min', body: 'El código TRENT14 te da un 14% de descuento en tu primera compra. En el último paso del pago, antes de confirmar, introduce el código en el campo "cupón" o "código promocional". Solo es válido una vez por cuenta. Si no te funciona, asegúrate de que es tu primera compra y de que lo escribes en mayúsculas: TRENT14.' },
    { tag: 'DEVOLUCIÓN', title: 'Cómo devolver o cambiar', read: '5 min', body: 'Si el producto llega defectuoso o no es lo que pediste, abre una disputa en la app de Hacoo en las primeras 72 horas desde la entrega. Ve a "Mis pedidos", selecciona el producto y pulsa "Problema con el pedido". Adjunta fotos claras del problema. Hacoo suele resolver en 3-5 días con reembolso o reenvío gratuito.' },
    { tag: 'CONTACTO', title: 'Soporte y preguntas frecuentes', read: '2 min', body: 'Para cualquier duda sobre tallas, envíos o incidencias, escríbeme directamente al canal de Telegram. Respondo personalmente a todos los mensajes. Para incidencias con Hacoo (producto mal, no llega, etc.) usa el sistema de disputas de la propia app — es la vía más rápida para obtener solución.' },
    { tag: 'MARCAS', title: 'Conoce nuestras colecciones', read: '6 min', body: 'En el catálogo encontrarás réplicas y productos inspirados en marcas como Palm Angels, Corteiz, Stone Island, Nude Project, Rick Owens y muchas más. Todos los productos están verificados personalmente antes de publicarse. Uso el canal de Telegram para publicar los mejores drops cada día — únete para no perderte nada.' },
  ],

  faq: [
    { q: '¿Cómo aplico el código TRENT14?', a: 'En el último paso del pago, antes de confirmar, introduces el código TRENT14 en el campo de "cupón" o "código promocional". Solo funciona en tu primera compra.' },
    { q: '¿Cuánto tarda en llegar?', a: 'Entre 7 y 15 días normalmente. Recibes tracking para seguir tu pedido paso a paso.' },
    { q: '¿Cómo sé qué talla pedir?', a: 'En cada prenda tienes medidas en centímetros. El truco es comparar con una prenda que ya tengas y te quede bien. Usa nuestra calculadora de tallas.' },
    { q: '¿Puedo devolver si no me gusta?', a: 'Sí. Tienes 30 días desde que reciben el artículo. Contacta con nuestro equipo por Telegram y te guiaremos en el proceso.' },
    { q: '¿De dónde son las prendas?', a: 'Trabajamos con varios fabricantes de calidad. Todas las prendas pasan un control antes de llegar a ti.' },
    { q: '¿Hay más códigos además de TRENT14?', a: 'TRENT14 es el código de bienvenida. Síguenos en Telegram para ofertas exclusivas y códigos sorpresa.' },
  ],

  categories: ['Todo', 'Sneakers', 'Sudaderas', 'Camisetas', 'Pantalones', 'Chaquetas', 'Bolsos', 'Accesorios'],
  brands: ['Todas', 'TRENT', 'Nike', 'Adidas', 'Puma', 'Stüssy', 'Carhartt'],
};
