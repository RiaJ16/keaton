from PySide6.QtGui import QPalette, QColor

def apply_palette(app, theme_name):
    palette = QPalette()

    if theme_name == "dark":
        palette.setColor(QPalette.Window, QColor("#2b2b2b"))
        palette.setColor(QPalette.WindowText, QColor("#e0e0e0"))
        palette.setColor(QPalette.Base, QColor("#1e1e1e"))
        palette.setColor(QPalette.Text, QColor("#e0e0e0"))
        palette.setColor(QPalette.Mid, QColor("#555555"))
        palette.setColor(QPalette.Highlight, QColor("#007acc"))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))

    elif theme_name == "light":
        palette.setColor(QPalette.Window, QColor("#f8f9fa"))
        palette.setColor(QPalette.WindowText, QColor("#222222"))
        palette.setColor(QPalette.Base, QColor("#ffffff"))
        palette.setColor(QPalette.Text, QColor("#222222"))
        palette.setColor(QPalette.Mid, QColor("#aaaaaa"))
        palette.setColor(QPalette.Highlight, QColor("#0078d7"))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))

    elif theme_name == "parchment":
        palette.setColor(QPalette.Window, QColor("#f5f0d7"))
        palette.setColor(QPalette.WindowText, QColor("#3b2f2f"))
        palette.setColor(QPalette.Base, QColor("#fcf7e8"))
        palette.setColor(QPalette.Text, QColor("#2e1f0f"))
        palette.setColor(QPalette.Mid, QColor("#bca77d"))
        palette.setColor(QPalette.Highlight, QColor("#d1b97f"))
        palette.setColor(QPalette.HighlightedText, QColor("#1e1e1c"))

    elif theme_name == "zelda":
        palette.setColor(QPalette.Window, QColor("#1e2f1c"))
        palette.setColor(QPalette.WindowText, QColor("#f0e6c8"))
        palette.setColor(QPalette.Base, QColor("#243924"))
        palette.setColor(QPalette.Text, QColor("#f0e6c8"))
        palette.setColor(QPalette.Mid, QColor("#3b5d3b"))
        palette.setColor(QPalette.Highlight, QColor("#a89c4f"))
        palette.setColor(QPalette.HighlightedText, QColor("#1e2f1c"))

    app.setPalette(palette)
