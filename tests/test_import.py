def test_import_adapter():
    from nonebot.adapters.wxwork import Adapter, Bot, Message, MessageSegment

    assert Adapter.get_name() == "WxWork"
    assert MessageSegment.text("hi").data["text"] == "hi"
