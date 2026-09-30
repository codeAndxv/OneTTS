"""测试长文本分句切片。"""

from server.utils.text_splitter import split_text_into_sentences


def test_split_empty_or_short():
    assert split_text_into_sentences("") == []
    assert split_text_into_sentences("你好世界") == ["你好世界"]


def test_split_punctuation():
    text = "第一句话。第二句话！第三句话？第四句话。"
    res = split_text_into_sentences(text)
    assert len(res) == 4
    assert res[0] == "第一句话。"
    assert res[1] == "第二句话！"
    assert res[2] == "第三句话？"
    assert res[3] == "第四句话。"


def test_split_max_length_limit():
    long_text = "这是一段非常非常长的文字，没有任何句号，连续输入超过限制长度。"
    res = split_text_into_sentences(long_text, max_chars=10)
    assert len(res) > 1
    assert all(len(c) <= 10 for c in res)
