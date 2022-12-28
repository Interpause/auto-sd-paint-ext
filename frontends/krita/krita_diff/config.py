from collections import OrderedDict
from dataclasses import asdict
from typing import Any

from krita import QObject, QReadWriteLock, QSettings

from .defaults import (
    CFG_FOLDER,
    CFG_GLOBAL,
    CFG_PRESET,
    ERR_MISSING_CONFIG,
    PRESET_DEFAULT,
    PRESET_NAMESPACE,
)

# Generalize Config further
# PresetConfig
# - specify GlobalConfig datamodel
# - specify which GlobalConfig key determines preset
# - Load all available presets by globbing a folder
# - Folder contains preset datamodel & webui config (which is dynamic)
# - New class for webUI config that allows checking for valid keys based on list rather than datamodel


class Config(QObject):
    def __init__(self, name, folder=CFG_FOLDER, model=None):
        """Sorta like a controller for QSettings.

        If model is None, Config will not check if keys exist.

        Args:
            name (str): Name of settings file.
            folder (str, optional): Which folder to store settings in. Defaults to CFG_FOLDER.
            model (Any, optional): Data model representing config & defaults. Defaults to None.
        """
        # See: https://doc.qt.io/qt-6/qsettings.html#accessing-settings-from-multiple-threads-or-processes-simultaneously
        # but im too lazy to figure out creating separate QSettings per worker, so we will just lock
        super(Config, self).__init__()
        self.model = model  # is immutable
        self.lock = QReadWriteLock()
        self.config = QSettings(QSettings.IniFormat, QSettings.UserScope, folder, name)

        # add in new config settings
        self.restore_defaults(overwrite=False)

    def __call__(self, key: str, type: type = str, preset: str = PRESET_DEFAULT):
        """Shorthand for Config.get()"""
        return self.get(key, type, preset)

    def get(self, key: str, type: type = str, preset: str = PRESET_DEFAULT):
        """Get config value by key & cast to type.

        Args:
            key (str): Name of config option.
            type (type, optional): Type to cast config value to. Defaults to str.
            preset (str, optional): Which preset to get value from. Defaults to PRESET_DEFAULT.

        Returns:
            Any: Config value.
        """
        full_key = f"{PRESET_NAMESPACE}/{preset}/{key}"
        self.lock.lockForRead()
        try:
            # notably QSettings assume strings too unless specified
            if self.model is not None:
                assert self.config.contains(full_key) and hasattr(
                    self.model, key
                ), ERR_MISSING_CONFIG
            # Maybe detect type from config datamodel instead?
            val = self.config.value(full_key, type=type)
            return val
        finally:
            self.lock.unlock()

    def set(
        self, key: str, val: Any, overwrite: bool = True, preset: str = PRESET_DEFAULT
    ):
        """Set config value by key.

        Args:
            key (str): Name of config option.
            val (Any): Config value.
            overwrite (bool, optional): Whether to overwrite an existing value. Defaults to False.
            preset (str, optional): Which preset to write value to. Defaults to PRESET_DEFAULT.
        """
        full_key = f"{PRESET_NAMESPACE}/{preset}/{key}"
        self.lock.lockForWrite()
        try:
            if self.model is not None:
                assert hasattr(self.model, key), ERR_MISSING_CONFIG
            if overwrite or not self.config.contains(full_key):
                self.config.setValue(full_key, val)
        finally:
            self.lock.unlock()

    def restore_defaults(self, overwrite: bool = True, preset: str = PRESET_DEFAULT):
        """Reset settings to default.

        Args:
            overwrite (bool, optional): Whether to overwrite existing settings, else add only new ones. Defaults to True.
            preset (str, optional): Which preset to reset to default. Defaults to PRESET_DEFAULT.
        """
        if self.model is None:
            if overwrite:
                try:
                    self.lock.lockForWrite()
                    self.config.remove(f"{PRESET_NAMESPACE}/{preset}")
                finally:
                    self.lock.unlock()
            return
        defaults = asdict(self.model)
        for k, v in defaults.items():
            self.set(k, v, overwrite, preset)

    def create_preset(self, preset: str):
        """Create a preset using Config.restore_defaults().

        Will raise AssertionError if the preset already exists.

        Args:
            preset (str): Preset to create.
        """
        try:
            self.lock.lockForRead()
            assert (
                f"{PRESET_NAMESPACE}/{preset}" in self.config.childGroups()
            ), "Preset already exists!"
        finally:
            self.lock.unlock()

        self.restore_defaults(True, preset)

    def delete_preset(self, preset: str):
        """Delete an existing preset.

        Args:
            preset (str): Preset to delete.
        """
        try:
            self.lock.lockForWrite()
            self.config.remove(f"{PRESET_NAMESPACE}/{preset}")
        finally:
            self.lock.unlock()


class PresetConfig(QObject):
    def __init__(self, folder=CFG_FOLDER) -> None:
        super(PresetConfig, self).__init__()

        self.global_cfgs = CFG_GLOBAL
        self.preset_cfgs = CFG_PRESET

        # Don't allow conflicting keys between datamodels to prevent glitches
        assert (
            len(
                set.intersection(
                    *[v().__dict__.keys() for v in self.cfgs.values() if v is not None]
                )
            )
            == 0
        ), "Config datamodels have conflicting keys!"

    @property
    def cfgs(self):
        return OrderedDict(
            list(self.global_cfgs.items()) + list(self.preset_cfgs.items())
        )

    def __call__(self, key: str, type: type = str):
        """Shorthand for Config.get()"""
        return self.get(key, type)

    def get(self, key: str, type: type = str):
        """Get config value by key & cast to type.

        Args:
            key (str): Name of config option.
            type (type, optional): Type to cast config value to. Defaults to str.

        Returns:
            Any: Config value.
        """
