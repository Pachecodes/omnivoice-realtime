from omnivoice_realtime.text_chunker import TextChunker


def test_chunker_flushes_complete_spanish_sentence():
    chunker = TextChunker(max_chars=120)

    chunks = chunker.push("Hola mundo. Esto queda pendiente")

    assert chunks == ["Hola mundo."]
    assert chunker.flush() == ["Esto queda pendiente"]


def test_chunker_splits_long_text_on_safe_boundary():
    chunker = TextChunker(max_chars=35)

    chunks = chunker.push("Esta primera parte es larga, pero todavía puede hablar bien")

    assert chunks == ["Esta primera parte es larga,"]
    assert chunker.flush() == ["pero todavía puede hablar bien"]
