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


def test_config_files_watcher_triggers_on_modify(temp_toml_file, monkeypatch):
    handler = mock.Mock()
    watcher = ConfigFilesWatcher(handler)

    # Patch settings._loaded_files to include our temp file
    monkeypatch.setattr("pururu.config.settings._loaded_files", [temp_toml_file])

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
    # not using assert_called_once because the event might be triggered multiple times due to file system events
    assert_that(handler.on_configuration_files_changed.called, equal_to(True))


def test_config_files_watcher_no_files(monkeypatch):
    handler = mock.Mock()
    watcher = ConfigFilesWatcher(handler)
    monkeypatch.setattr("pururu.config.settings._loaded_files", [])
    watcher.start_config_watcher()
    assert_that(watcher.config_observer, equal_to(None))
