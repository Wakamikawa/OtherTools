from colortool import ColorInfo, extract_color_structure


def repeated(color, count):
    return [color] * count


def test_small_warm_jump_becomes_accent_not_main_or_auxiliary():
    colors = []
    colors += repeated(ColorInfo(26, 45, 82), 4200)
    colors += repeated(ColorInfo(45, 73, 110), 2800)
    colors += repeated(ColorInfo(132, 178, 205), 950)
    colors += repeated(ColorInfo(190, 88, 34), 160)

    main, auxiliary, accents = extract_color_structure(colors)

    assert main
    assert all(stat.color != ColorInfo(190, 88, 34) for stat in main)
    assert all(stat.color != ColorInfo(190, 88, 34) for stat in auxiliary)
    assert accents
    assert accents[0].color == ColorInfo(190, 88, 34)


def test_small_near_main_color_is_not_accent():
    colors = []
    colors += repeated(ColorInfo(26, 45, 82), 4200)
    colors += repeated(ColorInfo(45, 73, 110), 2800)
    colors += repeated(ColorInfo(132, 178, 205), 950)
    colors += repeated(ColorInfo(54, 84, 123), 160)

    _main, _auxiliary, accents = extract_color_structure(colors)

    assert accents == []


def test_large_contrasting_red_moves_to_auxiliary_layer():
    colors = []
    colors += repeated(ColorInfo(35, 32, 23), 3400)
    colors += repeated(ColorInfo(51, 69, 41), 2200)
    colors += repeated(ColorInfo(93, 127, 71), 1800)
    colors += repeated(ColorInfo(147, 73, 57), 850)
    colors += repeated(ColorInfo(78, 41, 30), 180)
    colors += repeated(ColorInfo(128, 116, 86), 270)

    main, auxiliary, accents = extract_color_structure(colors)

    main_hex = {stat.color.hex_text for stat in main}
    auxiliary_hex = {stat.color.hex_text for stat in auxiliary}

    assert "#934939" not in main_hex
    assert "#934939" in auxiliary_hex
    assert "#4E291E" in auxiliary_hex or "#807456" in auxiliary_hex
    assert accents == []


def test_unexplained_sky_blue_backfills_auxiliary_layer():
    colors = []
    colors += repeated(ColorInfo(138, 137, 97), 3800)
    colors += repeated(ColorInfo(201, 196, 153), 1350)
    colors += repeated(ColorInfo(241, 244, 244), 560)
    colors += repeated(ColorInfo(50, 62, 51), 2950)
    colors += repeated(ColorInfo(114, 170, 202), 520)
    colors += repeated(ColorInfo(83, 164, 58), 420)

    _main, auxiliary, _accents = extract_color_structure(colors)

    auxiliary_hex = {stat.color.hex_text for stat in auxiliary}
    assert "#72AACA" in auxiliary_hex
    assert "#53A43A" in auxiliary_hex


def test_small_orange_boat_detail_backfills_accent_layer():
    colors = []
    colors += repeated(ColorInfo(78, 178, 206), 4600)
    colors += repeated(ColorInfo(86, 193, 178), 1500)
    colors += repeated(ColorInfo(58, 104, 141), 1400)
    colors += repeated(ColorInfo(80, 211, 158), 460)
    colors += repeated(ColorInfo(196, 130, 57), 70)

    _main, _auxiliary, accents = extract_color_structure(colors)

    accent_hex = {stat.color.hex_text for stat in accents}
    assert "#C48239" in accent_hex
