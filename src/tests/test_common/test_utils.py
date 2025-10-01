import pytest
from datetime import datetime
from enum import Enum
from unittest.mock import patch, MagicMock

from hamcrest import assert_that, equal_to, contains_string

from pururu.common.utils import get_banner, serialize, deserialize


class TestEnum(Enum):
    VALUE_ONE = "value_one"
    VALUE_TWO = "value_two"


# Test get_banner()
@patch('pururu.common.utils.get_version')
def test_get_banner_sets_version_correctly(mock_get_version):
    # Arrange
    mock_get_version.return_value = "1.2.3"
    
    # Act
    banner = get_banner()
    
    # Assert
    assert_that(banner, contains_string("1.2.3"))


# Test serialize() - parameterized for each conditional case
@pytest.mark.parametrize("input_value,expected", [
    # Dict case
    ({"key": "value"}, {"key": "value"}),
    # List case  
    (["item1", "item2"], ["item1", "item2"]),
    # Datetime case
    (datetime(2023, 8, 10, 15, 30, 45), "2023-08-10T15:30:45"),
    # Enum case
    (TestEnum.VALUE_ONE, "value_one"),
    # Nested cases
    ({"nested": [datetime(2023, 8, 10, 12, 0, 0)]}, {"nested": ["2023-08-10T12:00:00"]}),
    ([TestEnum.VALUE_TWO, {"enum": TestEnum.VALUE_ONE}], ["value_two", {"enum": "value_one"}])
])
def test_serialize_conditional_cases(input_value, expected):
    # When
    result = serialize(input_value)
    
    # Then
    assert_that(result, equal_to(expected))


# Test deserialize() - parameterized for each conditional case
@pytest.mark.parametrize("field_type,input_value,expected", [
    # None case
    (str, None, None),
    # Datetime case
    (datetime, "2023-08-10T15:30:45", datetime(2023, 8, 10, 15, 30, 45)),
    # List case with type args
    (list[str], ["item1", "item2"], ["item1", "item2"]),
    # List case with datetime
    (list[datetime], ["2023-08-10T10:00:00"], [datetime(2023, 8, 10, 10, 0, 0)]),
    # Enum case
    (TestEnum, "value_one", TestEnum.VALUE_ONE),
    # Regular value case
    (str, "simple_value", "simple_value")
])
def test_deserialize_conditional_cases(field_type, input_value, expected):
    # When
    result = deserialize(field_type, input_value)
    
    # Then
    assert_that(result, equal_to(expected))
