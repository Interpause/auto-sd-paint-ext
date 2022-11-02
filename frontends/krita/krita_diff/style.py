# NOTE: see https://bugreports.qt.io/browse/QTBUG-22862
# We cant set layout padding via stylesheet

style = """
QTabBar::tab {
    padding: 4px 2px 4px 2px;
}
"""
