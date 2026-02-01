from escrow_bot.ui.render import render_admin_dashboard


def test_admin_dashboard_render():
    assert "Admin Panel" in render_admin_dashboard()
