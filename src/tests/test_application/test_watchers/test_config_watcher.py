import os
import tempfile
import time
from unittest import mock

import pytest
from hamcrest import assert_that, equal_to

from pururu.application.watchers.config_watcher import ConfigFilesWatcher


@pytest.fixture
def temp_toml_file():
    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
        f.write(b"key = 'value'")
        f.flush()
        yield f.name
    os.remove(f.name)


@pytest.mark.unit
@mock.patch('pururu.application.watchers.config_watcher.logger')
def test_config_files_watcher_triggers_on_modify(mock_logger, temp_toml_file, monkeypatch):
    """Test trigger sets trace context"""
    # Arrange
    handler = mock.Mock()
    watcher = ConfigFilesWatcher(handler)
    mock_logger.generate_trace_id.return_value = "test_trace_config_555"
    mock_logger.set_trace_context = mock.Mock()

    # Patch settings._loaded_files to include our temp file
    monkeypatch.setattr("pururu.config.settings._loaded_files", [temp_toml_file])

    # Act
    watcher.start_config_watcher()
    time.sleep(0.2)  # Let the observer start

    # Modify the file to trigger the event
    with open(temp_toml_file, "a") as f:
        f.write("\nkey2 = 'value2'")

    # Wait for the event to be processed
    for _ in range(10):
        if handler.on_configuration_files_changed.called:
            break
        time.sleep(0.2)

    watcher.stop_config_watcher()

    # Assert
    # not using assert_called_once because the event might be triggered multiple times due to file system events
    assert_that(handler.on_configuration_files_changed.called, equal_to(True))
    mock_logger.generate_trace_id.assert_called()
    mock_logger.set_trace_context.assert_called_with('test_trace_config_555')


@pytest.mark.unit
def test_config_files_watcher_no_files(monkeypatch):
    """Test no config files"""
    # Arrange
    handler = mock.Mock()
    watcher = ConfigFilesWatcher(handler)
    monkeypatch.setattr("pururu.config.settings._loaded_files", [])
    # Act
    watcher.start_config_watcher()
    # Assert
    assert_that(watcher.config_observer, equal_to(None))
