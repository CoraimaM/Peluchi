"""Seed idempotente: categorías, productos de ejemplo y usuarios iniciales.

Se ejecuta automáticamente al arrancar la API (si la BD está vacía) o manualmente:
    python -m app.seed
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Category, Product, User
from app.security import hash_password

CATEGORIES = [
    {"name": "Clásicos", "slug": "clasicos", "emoji": "🧸",
     "description": "Osos y peluches atemporales, los imprescindibles de toda colección."},
    {"name": "Kawaii", "slug": "kawaii", "emoji": "🐰",
     "description": "Dulces personajes japoneses de colores pastel."},
    {"name": "Mundo Animal", "slug": "mundo-animal", "emoji": "🦊",
     "description": "Zorros, gatos, dinosaurios y todas las especies del reino."},
    {"name": "Videojuegos", "slug": "videojuegos", "emoji": "🎮",
     "description": "Homenajes a los clásicos del gaming retro y moderno."},
    {"name": "Cine y Series", "slug": "cine-series", "emoji": "🎬",
     "description": "Personajes de películas, series y animación."},
    {"name": "Gigantes", "slug": "gigantes", "emoji": "🐼",
     "description": "Peluches de más de 60 cm para abrazar sin límites."},
    {"name": "Ediciones Limitadas", "slug": "ediciones-limitadas", "emoji": "⭐",
     "description": "Piezas numeradas y difíciles de encontrar."},
    {"name": "Retro", "slug": "retro", "emoji": "🕹️",
     "description": "Nostalgia ochentera y noventera en forma de peluche."},
]

# (nombre, categoría slug, precio, precio_tachado, stock, cm, emoji, marca, material, destacado, nuevo, descripción)
PRODUCTS = [
    # ---- Clásicos ----
    ("Oso Vintage Serie 1950 30cm", "clasicos", 34.95, 44.95, 12, 30, "🧸", "Peluchi Heritage", "Peluche mohair clásico", True, False,
     "Réplica de un oso de 1950 con botones de ojos, costuras a mano y suave relleno de algodón. Un clásico para coleccionistas."),
    ("Oso Carmesí 25cm Edición Aniversario", "clasicos", 39.95, None, 8, 25, "🧸", "Peluchi Heritage", "Peluche premium rojo", True, True,
     "Edición aniversario en rojo carmesí con lazo de satén y etiqueta bordada numerada."),
    ("Conejo Blanco 22cm Tradición", "clasicos", 24.95, 29.95, 20, 22, "🐇", "Peluchi Heritage", "Peluche suave PP", False, False,
     "Conejo blanco de pelaje larguísimo, orejas acolchadas y nariz bordada."),

    # ---- Kawaii ----
    ("Conejo Pastel Sleepy 20cm", "kawaii", 18.95, None, 30, 20, "🐰", "Kawaii Cutie", "Minky pastel", True, True,
     "Conejito dormilón en tonos pastel con cachetes rosados. ¡El superventas de la tienda!"),
    ("Gato Nube Dormilón 25cm", "kawaii", 21.95, 26.95, 18, 25, "🐱", "Kawaii Cutie", "Minky pastel", True, False,
     "Gato con forma de nube que cambia de expresión según el ángulo. Suave como una almohada."),
    ("Pato Bombín 18cm", "kawaii", 14.95, None, 40, 18, "🦆", "Kawaii Cutie", "Peluche corto PP", False, False,
     "Patinillo amarillo con cachetes sonrojados y patas naranjas. Perfecto para regalar."),
    ("Sirena Axolote Rosa 22cm", "kawaii", 22.95, None, 15, 22, "🌸", "Kawaii Cutie", "Minky pastel", False, True,
     "Axolote con aletas de sirena en rosa algodón. Edición primaveral de la colección Kawaii."),

    # ---- Mundo Animal ----
    ("Zorro Bosque Nórdico 28cm", "mundo-animal", 29.95, 36.95, 14, 28, "🦊", "Wild Woods", "Peluche denso PP", True, False,
     "Zorro ártico con pelaje gris nieve y cola esponjosa. Detalles de bordado a mano."),
    ("León Melena Dorada 35cm", "mundo-animal", 37.95, None, 10, 35, "🦁", "Wild Woods", "Peluche denso PP", False, False,
     "León con melena extra-esponjosa y expresión amigable. Ideal para colecciones de animales."),
    ("Dinosaurio Verde Suave 35cm", "mundo-animal", 32.95, None, 9, 35, "🦕", "Wild Woods", "Peluche relleno firme", False, True,
     "Tiranosaurio amigable en verde bosque con espinas acolchadas."),
    ("Pingüino Explorador 22cm", "mundo-animal", 19.95, 24.95, 25, 22, "🐧", "Wild Woods", "Peluche corto PP", False, False,
     "Pingüino con bufanda de rayas listo para la expedición polar."),
    ("Rana Bombín 15cm", "mundo-animal", 12.95, None, 35, 15, "🐸", "Wild Woods", "Peluche suave PP", False, False,
     "Rana verde con ojos saltones y sonrisa enorme. Tamaño perfecto para el escritorio."),

    # ---- Videojuegos ----
    ("Robot Pixel 8-Bit 18cm", "videojuegos", 23.95, None, 16, 18, "🤖", "PixelPlay", "Peluche pixelado", True, False,
     "Robot de estética 8-bit con costuras cuadradas que emulan píxeles. Homenaje al arcade."),
    ("Slime Azul 20cm Nivel 1", "videojuegos", 17.95, 21.95, 28, 20, "💧", "PixelPlay", "Peluche minky azul", True, True,
     "El mítico slime azul con carita sonriente. Sube de nivel con cada abrazo."),
    ("Hongo Power-Up 16cm", "videojuegos", 13.95, None, 45, 16, "🍄", "PixelPlay", "Peluche corto PP", False, False,
     "Hongo rojo con lunares blancos que da +1 vida a cualquier estantería."),
    ("Dragón Arcade 30cm", "videojuegos", 38.95, None, 7, 30, "🐉", "PixelPlay", "Peluche con alas articuladas", False, True,
     "Dragón morado con alas rellenas y cola escamada. Jefe final de la colección gaming."),

    # ---- Cine y Series ----
    ("Astronauta Galaxia 30cm", "cine-series", 31.95, 39.95, 11, 30, "🚀", "Screen Buddies", "Peluche espacial brillante", True, False,
     "Astronauta con traje plateado, casco transparente y parche bordado."),
    ("Monstruo Bajo la Cama 26cm", "cine-series", 26.95, None, 13, 26, "👾", "Screen Buddies", "Peluche luminoso PP", False, False,
     "Monstruo morado de ojos grandes... más miedo da que te dejes de querer."),
    ("Perro Espacial 24cm", "cine-series", 25.95, None, 19, 24, "🐶", "Screen Buddies", "Peluche suave PP", False, True,
     "Perrito con traje de astronauta y mochila cohete. Listo para la misión."),
    ("Gato Detective 27cm", "cine-series", 28.95, 34.95, 6, 27, "🐈‍⬛", "Screen Buddies", "Peluche clásico", False, False,
     "Gato negro con gabardina y sombrero de detective. Resuelve misterios de la estantería."),

    # ---- Gigantes ----
    ("Kozi Panda Gigante 80cm", "gigantes", 59.95, 74.95, 5, 80, "🐼", "Big Hugs", "Relleno extra suave", True, True,
     "Panda de 80 cm con brazos larguísimo para abrazos de maratón. Nuestro peluche más grande."),
    ("Pulpo Reversible 63cm", "gigantes", 44.95, None, 8, 63, "🐙", "Big Hugs", "Peluche reversible", True, False,
     "El famoso pulpo reversible: exterior de un color y boca de otro. Terapia antiestrés incluida."),
    ("Oso Caramelo Gigante 100cm", "gigantes", 79.95, 99.95, 3, 100, "🧸", "Big Hugs", "Relleno premium gigante", False, False,
     "Oso de un metro en tono caramelo. La pieza estrella para sorprender a alguien."),

    # ---- Ediciones Limitadas ----
    ("Dragón Fuego Edición Dorada 30cm", "ediciones-limitadas", 64.95, None, 4, 30, "🐲", "Peluchi Vault", "Peluche metálico dorado", True, True,
     "Solo 100 unidades numeradas. Pelaje dorado con brillo suave y placa de colección."),
    ("Cisne Negro Numerado 32cm", "ediciones-limitadas", 54.95, None, 5, 32, "🦢", "Peluchi Vault", "Pluma de terciopelo", False, False,
     "Cisne negro con alas de terciopelo y numeración grabada en el pie."),

    # ---- Retro ----
    ("Robot Retro 1960 20cm", "retro", 27.95, 33.95, 12, 20, "🤖", "Retro Toy Co.", "Peluche con detalles de lona", True, False,
     "Robot de juguete de los años 60 reinterpretado en peluche, con antenas y botones."),
    ("Mono Cassete 1985 24cm", "retro", 25.95, None, 10, 24, "🐒", "Retro Toy Co.", "Peluche tejido", False, False,
     "Mono con casete en la barriga y gafas de sol. Nostalgia pura de los 80."),
    ("Coche Carrera 1990 26cm", "retro", 29.95, None, 7, 26, "🏎️", "Retro Toy Co.", "Peluche con parches", False, True,
     "Coche de carreras de los 90 con números de competición bordados."),
]

ADMIN_EMAIL = settings.admin_email
ADMIN_PASSWORD = settings.admin_password
DEMO_EMAIL = "cliente@peluchi.es"
DEMO_PASSWORD = "cliente123"


def seed(db: Session) -> None:
    """Inserta datos iniciales solo si las tablas están vacías."""
    # ---- Categorías ----
    if db.scalar(select(func.count(Category.id))) == 0:
        for cat in CATEGORIES:
            db.add(Category(**cat))
        db.commit()

    # ---- Productos ----
    if db.scalar(select(func.count(Product.id))) == 0:
        cat_map = {c.slug: c.id for c in db.scalars(select(Category)).all()}
        for (
            name, cat_slug, price, compare_price, stock, size_cm, emoji,
            brand, material, is_featured, is_new, description,
        ) in PRODUCTS:
            base_slug = "".join(
                ch if ch.isalnum() else "-" for ch in name.lower()
            ).replace("--", "-").strip("-")
            db.add(
                Product(
                    name=name,
                    slug=base_slug,
                    description=description,
                    sku=f"PL-{base_slug[:12].upper()}",
                    price=price,
                    compare_price=compare_price,
                    stock=stock,
                    size_cm=size_cm,
                    emoji=emoji,
                    brand=brand,
                    material=material,
                    category_id=cat_map[cat_slug],
                    is_featured=is_featured,
                    is_new=is_new,
                )
            )
        db.commit()

    # ---- Usuarios ----
    if db.scalar(select(func.count(User.id))) == 0:
        db.add(
            User(
                email=ADMIN_EMAIL,
                full_name="Administradora Peluchi",
                hashed_password=hash_password(ADMIN_PASSWORD),
                role="admin",
                provider="local",
            )
        )
        db.add(
            User(
                email=DEMO_EMAIL,
                full_name="Cliente Demo",
                hashed_password=hash_password(DEMO_PASSWORD),
                role="user",
                provider="local",
            )
        )
        db.commit()
        print(f"[seed] Usuarios creados: {ADMIN_EMAIL} (admin) / {DEMO_EMAIL} (cliente)")


def run() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed(db)
        n_products = db.scalar(select(func.count(Product.id)))
        n_cats = db.scalar(select(func.count(Category.id)))
        print(f"[seed] BD lista -> {n_cats} categorias, {n_products} productos")
    finally:
        db.close()


if __name__ == "__main__":
    run()
