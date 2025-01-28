from mechanismaf import scale_rotate_translate_coord

def test_scale_rotate_translate_coord():
    coord = (1, 1)
    scaled = scale_rotate_translate_coord(coord, scale=2.0)
    assert scaled == (2.0, 2.0)
