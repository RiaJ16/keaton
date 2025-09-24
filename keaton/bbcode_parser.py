import bbcode
import html
import re

COLOR_MAP = {
    "#3366cc": "#2980b9",  # azul fuerte → azul más usable
    "#ffa500": "#a89c4f",  # naranja brillante → dorado neutro
    "#ffa500".upper(): "#a89c4f",  # asegurar que mayúsculas/minúsculas entren
    "#182319": "#555555",  # verde gris oscuro → gris medio
}


def normalize_color(value: str) -> str:
    if not value:
        return "inherit"
    color = value.strip().lower()
    return COLOR_MAP.get(color, color)


def build_bbcode_parser():
    parser = bbcode.Parser()

    # Negrita, cursiva, subrayado
    parser.add_simple_formatter("b", "<b>%(value)s</b>")
    parser.add_simple_formatter("i", "<i>%(value)s</i>")
    parser.add_simple_formatter("u", "<u>%(value)s</u>")

    # Extras
    parser.add_simple_formatter("dice", '<p style="color:#2980b9; text-decoration:none;">Esto es una tirada de dados: %(value)s</p>')

    # Separadores
    parser.add_simple_formatter("hr", "<hr>", standalone=True)
    parser.add_simple_formatter("lh", "<hr>")

    # Quote sin autor
    parser.add_simple_formatter("quote", "<blockquote>%(value)s</blockquote>")

    # Quote con autor → aquí está el fix
    parser.add_formatter(
        "quote",
        render_func=render_quote,
        standalone=False,
        same_tag_closes=True,
        strip=True
    )

    parser.add_formatter(
        "url",
        render_func=lambda tag_name, value, options, parent, context:
            f"<a href='{clean_url(options.get(tag_name, ''))}'>{value}</a>",
        standalone=False,
        same_tag_closes=True,
        strip=True
    )

    # Colores [color=#ff0000]texto[/color]
    parser.add_formatter(
        "color",
        render_func=lambda tag_name, value, options, parent, context:
            f"<span style='color:{normalize_color(options.get(tag_name,'black'))}'>{value}</span>",
        standalone=False,
        strip=True
    )

    # Spoiler
    parser.add_formatter(
        "spoiler",
        render_func=lambda tag_name, value, options, parent, context:
        f"""
                <table border="0" cellspacing="0" cellpadding="0" width="100%">
                    <tr>
                        <td width="30"></td>
                        <td width="5" bgcolor="#c0392b"></td>
                        <td bgcolor="#25000000" style="padding-left: 8px;">
                            <b>Spoiler:</b><br>{value}
                        </td>
                    </tr>
                </table>
                """,
        standalone=False,
        strip=True
    )

    parser.add_formatter(
        "img",
        replace_links=False,
        render_func=lambda tag_name, value, options, parent, context: (
            f'<a href="{clean_url(value.strip())}"><img src="{clean_url(value.strip())}" style="max-width:100%; max-height:400px;"></a>'
        ),
        standalone=False,
        strip=True
    )

    parser.add_formatter(
        "image",
        replace_links=False,
        render_func=lambda tag_name, value, options, parent, context: (
            f'<a href="{clean_url(value.strip())}"><img src="{clean_url(value.strip())}" style="max-width:100%; max-height:400px;"></a>'
        ),
        standalone=False,
        strip=True
    )

    parser.add_formatter(
        "imagen",
        replace_links=False,
        render_func=lambda tag_name, value, options, parent, context: (
            f'<a href="{clean_url(value.strip())}"><img src="{clean_url(value.strip())}" style="max-width:100%; max-height:400px;"></a>'
        ),
        standalone=False,
        strip=True
    )

    parser.add_formatter(
        "centre",
        render_func=lambda tag_name, value, options, parent, context: (
            f'<div style="text-align:center">{value}</div>'
        ),
        standalone=False,
        strip=True
    )

    parser.add_formatter(
        "size",
        render_func=render_size,
        standalone=False,
        strip=True
    )

    parser.add_formatter(
        "youtube",
        render_func=lambda tag_name, value, options, parent, context: (
            f'<a href="https://www.youtube.com/watch?v={value.strip()}" '
            f'style="color:#e74c3c; text-decoration:none;">🎬 Ver en YouTube</a>'
        ),
        standalone=False,
        strip=True
    )

    return parser


def render_size(tag_name, value, options, parent, context):
    size = options.get(tag_name, "")
    try:
        size_val = int(size)
    except ValueError:
        size_val = 100  # default

    if size_val >= 200:
        return f"<h1>{value}</h1>"
    elif size_val >= 150:
        return f"<h2>{value}</h2>"
    elif size_val >= 120:
        return f"<h3>{value}</h3>"
    else:
        return f'<span style="font-size:{size_val}%">{value}</span>'


def render_quote(tag_name, value, options, parent, context):
    quoter = options.get(tag_name, "")
    if quoter:
        tagline = f"{quoter} dijo:<br>"
    else:
        tagline = ""
    return f"""
        <table border="0" cellspacing="0" cellpadding="0" width="100%">
            <tr>
                <td width="30"></td>
                <td width="5" bgcolor="#2980b9"></td>
                <td bgcolor="#25000000" style="padding-left: 8px;">
                    <b>{tagline}</b>{value}
                </td>
            </tr>
        </table>
        """


def clean_url(url: str) -> str:
    """Convierte entidades HTML (&...;) en sus caracteres reales y limpia espacios extra."""
    if not url:
        return url
    # Decodificar entidades HTML (&amp;, &#58;, &#46;, etc.)
    url = html.unescape(url)
    # Quitar espacios o saltos de línea molestos
    url = url.strip()
    # Asegurar que empiece con http o https
    # if not re.match(r'^https?://', url):
    #     url = "http://" + url  # fallback mínimo
    return url
