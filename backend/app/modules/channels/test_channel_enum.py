from app.modules.channels.models import BotChannel, ChannelType
from app.modules.dialogs.models import Dialog


def test_channel_type_enum_uses_values() -> None:
    expected = [item.value for item in ChannelType]
    assert BotChannel.__table__.c.channel_type.type.enums == expected
    assert Dialog.__table__.c.channel_type.type.enums == expected


def test_channel_type_enum_validates_strings() -> None:
    assert BotChannel.__table__.c.channel_type.type.validate_strings is True
    assert Dialog.__table__.c.channel_type.type.validate_strings is True
