import waqd_station.app as app
import waqd_station.settings as setting_names


def test_app_singletons_follow_late_initialization(base_fixture):
    from waqd_station.app import comp_ctrl, settings, unit_reg

    original_comp_ctrl = comp_ctrl() if comp_ctrl else None
    original_settings = settings() if settings else None
    original_unit_reg = unit_reg() if unit_reg else None

    try:
        comp_ctrl.clear()
        settings.clear()
        unit_reg.clear()

        assert not comp_ctrl
        assert not settings
        assert not unit_reg

        app.basic_setup()

        assert unit_reg.Quantity(1, "degC").m_as(unit_reg.degC) == 1
        assert settings.get_string(setting_names.LANG) is not None
        assert comp_ctrl.components is app.comp_ctrl().components
    finally:
        comp_ctrl.clear()
        settings.clear()
        unit_reg.clear()
        if original_comp_ctrl is not None:
            comp_ctrl.replace(original_comp_ctrl)
        if original_settings is not None:
            settings.replace(original_settings)
        if original_unit_reg is not None:
            unit_reg.replace(original_unit_reg)