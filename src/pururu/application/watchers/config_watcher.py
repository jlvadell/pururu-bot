import os
import threading

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from pururu.application.handlers.background_event_handler import BackgroundEventHandler
from pururu.common import logger
from pururu.config import settings


class ConfigFilesWatcher(FileSystemEventHandler):
    def __init__(self, event_handler: BackgroundEventHandler):
        super().__init__()
        self.logger = logger.get_logger(__name__)
        self.event_handler = event_handler
        self.config_observer = None
        self.config_observer_thread = None

    def on_modified(self, event):
        self._handle_configuration_change_event(event)

    def on_created(self, event):
        self._handle_configuration_change_event(event)

    def on_moved(self, event):
        self._handle_configuration_change_event(event)

    def start_config_watcher(self):
        files_to_watch = [os.path.abspath(f) for f in settings._loaded_files]
        if not files_to_watch:
            return
        paths_to_watch = {os.path.dirname(f) for f in files_to_watch}
        observer = Observer()
        for path in paths_to_watch:
            observer.schedule(self, path=path, recursive=False)
            self.logger.info(f"Started watching config files in: {path}")
        self.config_observer = observer

        def _start():
            observer.start()
            observer.join()

        thread = threading.Thread(target=_start, daemon=True)
        self.config_observer_thread = thread
        thread.start()

    def stop_config_watcher(self):
        self.logger.info("Stopping config watcher.")
        if self.config_observer:
            self.config_observer.stop()
            self.config_observer.join()
            self.logger.info("Stopped config watcher.")
        if self.config_observer_thread:
            self.config_observer_thread.join()
            self.logger.info("Config watcher thread joined.")

    def _handle_configuration_change_event(self, event):
        if event.src_path.endswith(".toml"):
            self.logger.info(f"Detected config change: {event.src_path}")
            self.event_handler.on_configuration_files_changed()
            self.logger.info("Configuration reloaded successfully.")
