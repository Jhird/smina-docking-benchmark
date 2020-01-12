import json
import os
from typing import List

import pandas as pd

import docking_benchmark.data.directories

PROTEIN_FORMATS = (
    '.pdb',
    '.pdbqt',
)


class Datasets:
    _DEFAULT_SMILES_COLUMN = 'SMILES'
    _DEFAULT_SCORE_COLUMN = 'DOCKING_SCORE'

    def __init__(self, protein):
        self.protein = protein
        self._datasets = protein.metadata.get('datasets', list())

    def __getitem__(self, dataset_name):
        if dataset_name not in self._datasets:
            raise KeyError(f'No dataset named {dataset_name} for protein {self.protein.name}')

        dataset = self._datasets[dataset_name]
        csv = pd.read_csv(os.path.join(self.protein.directory, dataset['path']))
        smiles_column = dataset.get('smiles_column', self._DEFAULT_SMILES_COLUMN)
        score_column = dataset.get('score_column', self._DEFAULT_SCORE_COLUMN)
        return csv[smiles_column].tolist(), csv[score_column].to_numpy()

    @property
    def default(self):
        return self['default']


class Protein:
    """Container for protein-related data.

    The class provides required protein information
    for SMINA docking software.

    Single protein's data must be put into one directory.
    This directory *must* contain a `metadata.json` file
    and a *single* file with .pdb/.pdbqt extension.

    `metadata.json` stores basic information about protein,
    such as its pocket center coordinates and available datasets
    associated with it.

    See the example below for `metadata.json` file structure.

    Example `metadata.json` file:
    ```json
    {
        "pocket_center": [0.0, 0.0, 0.0],
        "datasets": {
            "first_dataset": {
                "path": "datasets/first.csv",
                "smiles_column": "smi",
                "score_column": "activity"
            },
            "second_dataset": {
                "path": "datasets/second.csv"
            }
        }
    }
    ```

    `pocket_center` field *is required*.
    It must be a list of three numbers - coordinates used for docking.

    `datasets` key is optional.
    Each entry in the `datasets` dictionary *must* have `path` field present.
    `smiles_column` and `score_column` are optional.

    Attributes:
        name (str): Name of the protein, e.g. '5ht1b'.
        directory: Path to the directory containing protein related files.
        path: Path to the protein file.
        metadata (dict): Dictionary with parsed metadata.json file (see above for description).
        datasets (Datasets): Available datasets for the protein.
    """
    _METADATA_FILENAME = 'metadata.json'
    _POCKET_CENTER_LENGTH = 3

    def __init__(self, name: str, directory):
        """Creates a Protein from given directory.

        See the class-level docs for required directory structure.

        Args:
            name (str): Name of the protein.
            directory: Path to the directory containing protein related files.

        Raises:
            ValueError: If directory does not exist,
                        does not contain metadata.json file,
                        contains invalid metadata.json file
                        or does not contain a single .pdb/.pdbqt file.
        """
        if not os.path.exists(directory):
            raise ValueError(f'Directory {directory} does not exist')

        self.name = name
        self.directory = directory
        self.path = self._load_protein_file_path()
        self.metadata = self._load_metadata()
        self.datasets = Datasets(self)

    def _load_protein_file_path(self):
        """Returns protein file path from provided directory.

        The method looks for .pdb/.pdbqt file in provided directory.
        No validity check of the file is performed.

        Raises:
            ValueError: If no, or more than one .pdb/.pdbqt file
                        is present in the directory.

        Returns:
            Path to .pdb/.pdbqt file.
        """
        protein_files = [entry for entry in os.listdir(self.directory)
                         if any(entry.endswith(fmt) for fmt in PROTEIN_FORMATS)]

        if len(protein_files) != 1:
            msg_start = 'No protein files' if len(protein_files) == 0 else 'More than one protein file'
            raise ValueError(msg_start + ' inside ' + self.name + ' protein data directory')

        return os.path.join(self.directory, protein_files[0])

    def _load_metadata(self) -> dict:
        """Loads and parses `metadata.json` file from provided directory.

        Raises:
            ValueError: If `metadata.json file` does not exist or is invalid.

        Returns:
            dict: Parsed `metadata.json` file.
        """
        metadata_path = os.path.join(self.directory, self.__class__._METADATA_FILENAME)

        if not os.path.exists(metadata_path):
            raise ValueError('No metadata.json file for ' + self.name)

        with open(metadata_path) as metadata_file:
            metadata = json.load(metadata_file)

            if 'pocket_center' not in metadata:
                raise ValueError('Protein ' + self.name +
                                 ' metadata must contain pocket_center key')

            if len(metadata['pocket_center']) != self._POCKET_CENTER_LENGTH:
                raise ValueError('Pocket center for ' + self.name +
                                 'must be a list of three floats')

            for coordinate in metadata['pocket_center']:
                if type(coordinate) is not float:
                    raise ValueError('Pocket center for ' + self.name +
                                     'must be a list of three floats')

            return metadata

    @property
    def pocket_center(self) -> List[float]:
        """list[float]: Pocket center coordinates used for docking"""
        return self.metadata['pocket_center']


def get_proteins():
    return {
        protein_dir.lower(): Protein(
            protein_dir.lower(),
            os.path.join(docking_benchmark.data.directories.PROTEINS, protein_dir.lower())
        ) for protein_dir in os.listdir(docking_benchmark.data.directories.PROTEINS)}
