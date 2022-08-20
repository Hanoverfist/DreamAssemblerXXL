import os
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple, Union
from zipfile import ZIP_DEFLATED, ZipFile

from colorama import Fore
from structlog import get_logger

from gtnh.assembler.downloader import get_asset_version_cache_location
from gtnh.defs import ModSource, Side
from gtnh.models.gtnh_config import GTNHConfig
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import ExternalModInfo, GTNHModInfo
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


class GenericAssembler:
    """
    Generic assembler class.
    """

    def __init__(
        self,
        gtnh_modpack: GTNHModpackManager,
        release: GTNHRelease,
        task_progress_callback: Optional[Callable[[float, str], None]] = None,
        global_progress_callback: Optional[Callable[[float, str], None]] = None,
    ):
        """
        Constructor of the GenericAssembler class.

        :param gtnh_modpack: the modpack manager instance
        :param release: the target release object
        :param task_progress_callback: the callback to report the progress of the task
        :param global_progress_callback: the callback to report the global progress
        """
        self.modpack_manager: GTNHModpackManager = gtnh_modpack
        self.release: GTNHRelease = release
        self.global_progress_callback: Optional[Callable[[float, str], None]] = global_progress_callback
        self.task_progress_callback: Optional[Callable[[float, str], None]] = task_progress_callback
        self.exclusions: Dict[str, List[str]] = {
            Side.CLIENT: self.modpack_manager.mod_pack.client_exclusions,
            Side.SERVER: self.modpack_manager.mod_pack.server_exclusions,
        }
        self.delta_progress: float = 0.0

    def get_progress(self) -> float:
        """
        Getter for self.delta_progress.

        :return: current delta progress value
        """
        return self.delta_progress

    def set_progress(self, delta_progress: float) -> None:
        """
        Setter for self.delta_progress.

        :param delta_progress: the new delta progress
        :return: None
        """
        self.delta_progress = delta_progress

    def get_amount_of_files_in_config(self, side: Side) -> int:
        """
        Method to get the amount of files inside the config zip.

        :param side: targetted side for the release
        :return: the amount of files
        """
        modpack_config: GTNHConfig
        config_version: GTNHVersion

        modpack_config, config_version = self.get_config()
        config_file: Path = get_asset_version_cache_location(modpack_config, config_version)

        with ZipFile(config_file, "r", compression=ZIP_DEFLATED) as config_zip:
            return len([item for item in config_zip.namelist() if item not in self.exclusions[side]])

    def get_mods(self, side: Side) -> List[Tuple[GTNHModInfo | ExternalModInfo, GTNHVersion]]:
        """
        Method to grab the mod info objects as well as their targetted version.

        :param side: the targetted side
        :return: a list of couples where the first object is the mod info object, the second is the targetted version.
        """
        get_mod: Callable[
            [str, str, Set[Side], ModSource], Optional[tuple[Union[GTNHModInfo, ExternalModInfo], GTNHVersion]]
        ] = self.modpack_manager.assets.get_mod_and_version
        valid_sides: Set[Side] = {side, Side.BOTH}

        github_mods: List[Optional[Tuple[GTNHModInfo | ExternalModInfo, GTNHVersion]]] = [
            get_mod(name, version, valid_sides, ModSource.github) for name, version in self.release.github_mods.items()
        ]

        external_mods: List[Optional[Tuple[GTNHModInfo | ExternalModInfo, GTNHVersion]]] = [
            get_mod(name, version, valid_sides, ModSource.github)
            for name, version in self.release.external_mods.items()
        ]

        mods: List[Tuple[GTNHModInfo | ExternalModInfo, GTNHVersion]] = list(filter(None, github_mods + external_mods))
        return mods

    def get_config(self) -> Tuple[GTNHConfig, GTNHVersion]:
        """
        Method to get the config file from the release.

        :return: a tuple with the GTNHConfig and GTNHVersion of the release's config
        """

        config: GTNHConfig = self.modpack_manager.assets.config
        version: Optional[GTNHVersion] = config.get_version(self.release.config)
        assert version
        return config, version

    def add_mods(
        self, side: Side, mods: list[tuple[GTNHModInfo, GTNHVersion]], archive: ZipFile, verbose: bool = False
    ) -> None:
        """
        Method to add mods in the zip archive.

        :param side: target side
        :param mods: target mods
        :param archive: archive being built
        :param verbose: flag to turn on verbose mode
        :return: None
        """
        pass

    def add_config(
        self, side: Side, config: Tuple[GTNHConfig, GTNHVersion], archive: ZipFile, verbose: bool = False
    ) -> None:
        """
        Method to add config in the zip archive.

        :param side: target side
        :param config: a tuple giving the config object and the version object of the config
        :param archive: archive being built
        :param verbose: flag to turn on verbose mode
        :return: None
        """
        pass

    def update_progress(self, side: Side, source_file: Path, verbose: bool = False) -> None:
        """
        Method used to report progress.

        :param side: target side
        :param source_file: file path being added
        :param verbose: flag to turn on verbose mode
        :return: None
        """
        pass

    def assemble(self, side: Side, verbose: bool = False) -> None:
        """
        Method to assemble the release.

        :param side: target side
        :param verbose: flag to enable the verbose mode
        :return: None
        """
        if side not in {Side.CLIENT, Side.SERVER}:
            raise Exception("Can only assemble release for CLIENT or SERVER, not BOTH")

        archive_name: Path = self.get_archive_path(side)

        # deleting any existing archive
        if os.path.exists(archive_name):
            os.remove(archive_name)
            log.warn(f"Previous archive {Fore.YELLOW}'{archive_name}'{Fore.RESET} deleted")

        log.info(f"Constructing {Fore.YELLOW}{side}{Fore.RESET} archive at {Fore.YELLOW}'{archive_name}'{Fore.RESET}")

        with ZipFile(self.get_archive_path(side), "w") as archive:
            log.info("Adding mods to the archive")
            self.add_mods(side, self.get_mods(side), archive, verbose=verbose)
            log.info("Adding config to the archive")
            self.add_config(side, self.get_config(), archive, verbose=verbose)
            log.info("Archive created successfully!")

    def get_archive_path(self, side: Side) -> Path:
        """
        Method to get the path to the assembled pack release.

        :return: the path to the release
        """
        pass