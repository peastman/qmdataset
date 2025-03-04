from qcportal import PortalClient
from qcportal.singlepoint import QCSpecification, SinglepointDatasetNewEntry
from qcportal.molecules import Molecule
from qcportal.utils import chunk_iterable
from openmm.unit import nanometer, bohr
import openff.toolkit
import numpy as np
import h5py
import sys

dataset_name = sys.argv[1]
client = PortalClient.from_file()
scale = (1*nanometer).value_in_unit(bohr)
keywords = {'maxiter': 200,
            'scf_properties': ['dipole', 'quadrupole', 'wiberg_lowdin_indices', 'mayer_indices', 'mbis_charges'],
            'wcombine': False}
spec = QCSpecification(program='psi4', driver='gradient', method='wb97m-d3bj', basis='def2-tzvppd', keywords=keywords)
entries = []
for filename in sys.argv[2:]:
    input_file = h5py.File(filename)
    for i, group in enumerate(input_file):
        smiles = input_file[group]['smiles'].asstr()[0]
        conformations = np.array(input_file[group]['conformations'])*scale
        ffmol = openff.toolkit.topology.Molecule.from_mapped_smiles(smiles, allow_undefined_stereo=True)
        symbols = [atom.symbol for atom in ffmol.atoms]
        total_charge = sum(atom.formal_charge.m for atom in ffmol.atoms)
        total_atomic_number = sum(atom.atomic_number for atom in ffmol.atoms)
        multiplicity = 1 if (total_charge+total_atomic_number) % 2 == 0 else 2
        identifiers = {'canonical_isomeric_explicit_hydrogen_mapped_smiles': smiles}
        for i, conformation in enumerate(conformations):
            try:
                molecule = Molecule(symbols=symbols, geometry=conformation.flatten(), molecular_charge=total_charge, molecular_multiplicity=multiplicity, identifiers=identifiers, extras=identifiers)
                entries.append(SinglepointDatasetNewEntry(name=f'{group}-{i}', molecule=molecule))
            except Exception as ex:
                print(ex)
                pass
dataset = client.add_dataset('singlepoint', dataset_name)
dataset.add_specification('wb97m-d3bj/def2-tzvppd', spec)
for batch in chunk_iterable(entries, 1000):
    dataset.add_entries(batch)
dataset.submit(tag='spice-psi4-181')
