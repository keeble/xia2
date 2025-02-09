from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
from typing import List

import pytest

from dials.array_family import flex
from dxtbx.serialize import load

from xia2.Modules.SSX.data_reduction_programs import determine_best_unit_cell


def check_output(main_dir, find_spots=False, index=False, integrate=False):

    assert find_spots is (main_dir / "batch_1" / "strong.refl").is_file()
    assert index is (main_dir / "batch_1" / "indexed.expt").is_file()
    assert index is (main_dir / "batch_1" / "indexed.refl").is_file()
    assert integrate is (main_dir / "batch_1" / "integrated_1.expt").is_file()
    assert integrate is (main_dir / "batch_1" / "integrated_1.refl").is_file()
    assert (main_dir / "LogFiles" / "xia2.ssx.log").is_file()
    assert integrate is (main_dir / "DataFiles" / "integrated_1_batch_1.expt").is_file()
    assert integrate is (main_dir / "DataFiles" / "integrated_1_batch_1.expt").is_file()


@pytest.mark.parametrize(
    "option,expected_success",
    [
        ("assess_crystals.images_to_use=3:5", [True, False, True]),
        ("batch_size=2", [False, False, True, False, True]),
        ("assess_crystals.n_crystals=2", [False, False, True, False, True]),
    ],
)
def test_assess_crystals(dials_data, tmp_path, option, expected_success):
    """
    Test a basic run. Expect to import and then do crystal assessment,
    and nothing more (for now).

    The options test the two modes of operation - either assess a specific
    image range or process cumulatively in batches until a given number of
    crystals are indexed, or all images are used.
    """

    ssx = dials_data("cunir_serial", pathlib=True)
    # Set the max cell to avoid issue of a suitable max cell not being found
    # due to very thin batch size.
    with (tmp_path / "index.phil").open(mode="w") as f:
        f.write("indexing.max_cell=150")
    args = ["xia2.ssx", option, "indexing.phil=index.phil"]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr

    # want to test
    assert (tmp_path / "import").is_dir()
    assert (tmp_path / "import" / "file_input.json").is_file()

    with (tmp_path / "import" / "file_input.json").open(mode="r") as f:
        file_input = json.load(f)
        assert file_input["reference_geometry"] is None
        assert file_input["images"] == [os.fspath(ssx / "merlin0047_1700*.cbf")]

    assert (tmp_path / "assess_crystals").is_dir()
    assert (tmp_path / "assess_crystals" / "assess_crystals.json").is_file()
    assert (tmp_path / "assess_crystals" / "dials.cell_clusters.html").is_file()

    with open(tmp_path / "assess_crystals" / "assess_crystals.json", "r") as f:
        data = json.load(f)
    assert data["success_per_image"] == expected_success


@pytest.mark.parametrize(
    "option,expected_success",
    [
        ("geometry_refinement.images_to_use=3:5", [True, True, True]),
        ("batch_size=2", [False, True, True, True, True]),
        ("geometry_refinement.n_crystals=2", [False, True, True, True, True]),
    ],
)
def test_geometry_refinement(dials_data, tmp_path, option, expected_success):
    ssx = dials_data("cunir_serial", pathlib=True)
    # Set the max cell to avoid issue of a suitable max cell not being found
    # due to very thin batch size.
    with (tmp_path / "index.phil").open(mode="w") as f:
        f.write("indexing.max_cell=150")
    args = [
        "xia2.ssx",
        "steps=None",
        "unit_cell=96.4,96.4,96.4,90,90,90",
        "space_group=P213",
        option,
        "indexing.phil=index.phil",
        "max_lattices=1",
    ]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr

    # Check that the processing went straight to geometry refinement and then
    # stopped before processing the batches
    assert not (tmp_path / "assess_crystals").is_dir()
    assert (tmp_path / "geometry_refinement").is_dir()
    reference = tmp_path / "geometry_refinement" / "refined.expt"
    assert reference.is_file()
    assert not (tmp_path / "batch_1").is_dir()

    # Test the data was reimported correctly ready for next run
    assert (tmp_path / "import").is_dir()
    assert (tmp_path / "import" / "file_input.json").is_file()
    assert (tmp_path / "import" / "imported.expt").is_file()
    with (tmp_path / "import" / "file_input.json").open(mode="r") as f:
        file_input = json.load(f)
        assert file_input["reference_geometry"] == os.fspath(reference)
        assert file_input["images"] == [os.fspath(ssx / "merlin0047_1700*.cbf")]

    # Inspect the output to check which images were used in refinement.
    assert (tmp_path / "geometry_refinement" / "geometry_refinement.json").is_file()
    assert (tmp_path / "geometry_refinement" / "dials.cell_clusters.html").is_file()
    with open(tmp_path / "geometry_refinement" / "geometry_refinement.json", "r") as f:
        data = json.load(f)
    assert data["success_per_image"] == expected_success
    refined_expts = load.experiment_list(reference, check_format=False)
    assert len(refined_expts) == sum(expected_success)
    assert len(refined_expts.beams()) == 1
    assert len(refined_expts.detectors()) == 1

    assert (tmp_path / "DataFiles" / "refined.expt").is_file()
    assert (tmp_path / "LogFiles" / "dials.refine.log").is_file()


@pytest.fixture
def refined_expt(dials_data, tmp_path):
    ssx = dials_data("cunir_serial", pathlib=True)

    args = [
        "xia2.ssx",
        "steps=None",
        "unit_cell=96.4,96.4,96.4,90,90,90",
        "space_group=P213",
    ]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr

    assert (tmp_path / "geometry_refinement").is_dir()
    reference = tmp_path / "geometry_refinement" / "refined.expt"
    assert reference.is_file()
    refined_expts = load.experiment_list(reference, check_format=False)

    shutil.rmtree(tmp_path / "DataFiles")
    shutil.rmtree(tmp_path / "LogFiles")
    return refined_expts


def test_run_with_reference(dials_data, tmp_path, refined_expt):
    """
    Test running with a supplied reference geometry from a refined.expt.
    """
    refined_expt.as_file(tmp_path / "refined.expt")

    ssx = dials_data("cunir_serial", pathlib=True)

    args = [
        "xia2.ssx",
        "unit_cell=96.4,96.4,96.4,90,90,90",
        "space_group=P213",
        "integration.algorithm=stills",
        f"reference_geometry={os.fspath(tmp_path / 'refined.expt')}",
        "steps=find_spots+index+integrate",
    ]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(tmp_path, find_spots=True, index=True, integrate=True)

    assert not (tmp_path / "DataFiles" / "refined.expt").is_file()
    assert not (tmp_path / "LogFiles" / "dials.refine.log").is_file()


def test_full_run_without_reference(dials_data, tmp_path):
    ssx = dials_data("cunir_serial", pathlib=True)

    args = [
        "xia2.ssx",
        "unit_cell=96.4,96.4,96.4,90,90,90",
        "space_group=P213",
        "integration.algorithm=stills",
        "d_min=2.0",
        "enable_live_reporting=True",
        "max_lattices=1",
    ]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr

    # Now check that the processing went straight to geometry refinement
    assert not (tmp_path / "assess_crystals").is_dir()
    assert (tmp_path / "geometry_refinement").is_dir()
    reference = tmp_path / "geometry_refinement" / "refined.expt"
    assert reference.is_file()
    assert (tmp_path / "DataFiles" / "refined.expt").is_file()
    assert (tmp_path / "LogFiles" / "dials.refine.log").is_file()

    # Now check that the data was reimported with this reference
    assert (tmp_path / "import" / "file_input.json").is_file()
    with (tmp_path / "import" / "file_input.json").open(mode="r") as f:
        file_input = json.load(f)
        assert file_input["reference_geometry"] == os.fspath(reference)
        assert file_input["images"] == [os.fspath(ssx / "merlin0047_1700*.cbf")]
    expts = tmp_path / "import" / "imported.expt"
    assert expts.is_file()
    with_reference_identifiers = load.experiment_list(
        expts, check_format=False
    ).identifiers()

    # Check that the data were integrated with this new reference geometry
    assert (tmp_path / "batch_1").is_dir()
    assert (tmp_path / "batch_1/nuggets").is_dir()
    sliced_expts = tmp_path / "batch_1" / "imported.expt"
    assert sliced_expts.is_file()
    sliced_identifiers = load.experiment_list(
        sliced_expts, check_format=False
    ).identifiers()
    assert with_reference_identifiers == sliced_identifiers
    check_output(tmp_path, find_spots=True, index=True, integrate=True)
    assert len(list((tmp_path / "batch_1/nuggets").glob("nugget_index*"))) == 5
    assert len(list((tmp_path / "batch_1/nuggets").glob("nugget_integrate*"))) == 5

    # Check that data reduction completed.
    check_data_reduction_files(tmp_path)


def test_stepwise_run_without_reference(dials_data, tmp_path):
    ssx = dials_data("cunir_serial", pathlib=True)

    args = [
        "xia2.ssx",
        "unit_cell=96.4,96.4,96.4,90,90,90",
        "space_group=P213",
        "integration.algorithm=stills",
        "d_min=2.0",
        "steps=find_spots+index+integrate",
    ]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))
    args.append("steps=find_spots")

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr

    # Now check that the processing went straight to geometry refinement
    assert not (tmp_path / "assess_crystals").is_dir()
    assert (tmp_path / "geometry_refinement").is_dir()
    reference = tmp_path / "geometry_refinement" / "refined.expt"
    assert reference.is_file()

    # Now check that the data was reimported with this reference
    assert (tmp_path / "import" / "file_input.json").is_file()
    with (tmp_path / "import" / "file_input.json").open(mode="r") as f:
        file_input = json.load(f)
        assert file_input["reference_geometry"] == os.fspath(reference)
        assert file_input["images"] == [os.fspath(ssx / "merlin0047_1700*.cbf")]
    expts = tmp_path / "import" / "imported.expt"
    assert expts.is_file()
    with_reference_identifiers = load.experiment_list(
        expts, check_format=False
    ).identifiers()

    # Check that find_spots was run with this new reference geometry
    assert (tmp_path / "batch_1").is_dir()
    sliced_expts = tmp_path / "batch_1" / "imported.expt"
    assert sliced_expts.is_file()
    sliced_identifiers = load.experiment_list(
        sliced_expts, check_format=False
    ).identifiers()
    assert with_reference_identifiers == sliced_identifiers
    check_output(tmp_path, find_spots=True)

    # Now rerun, check nothing further done if forgetting to specify geometry
    args[-1] = "steps=index"
    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(tmp_path, find_spots=True)

    # Now specify geometry
    args.append("reference_geometry=geometry_refinement/refined.expt")
    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(tmp_path, find_spots=True, index=True)

    # Now specify geometry
    args[-2] = "steps=integrate"
    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(tmp_path, find_spots=True, index=True, integrate=True)


def check_data_reduction_files(tmp_path, reindex=True, reference=False):
    assert (tmp_path / "data_reduction").is_dir()
    assert (tmp_path / "data_reduction" / "prefilter").is_dir()
    assert reindex is (tmp_path / "data_reduction" / "reindex").is_dir()
    assert reindex is (tmp_path / "LogFiles" / "dials.cosym.0.log").is_file()
    assert reindex is (tmp_path / "LogFiles" / "dials.cosym.0.html").is_file()
    assert (tmp_path / "data_reduction" / "scale").is_dir()
    assert (tmp_path / "data_reduction" / "scale" / "merged.mtz").is_file()
    assert (tmp_path / "DataFiles" / "merged.mtz").is_file()
    assert (tmp_path / "LogFiles" / "dials.merge.html").is_file()
    assert (tmp_path / "LogFiles" / "dials.merge.log").is_file()
    assert (tmp_path / "LogFiles" / "dials.merge.json").is_file()
    if reference:
        assert (tmp_path / "DataFiles" / "scaled_0.refl").is_file()
        assert (tmp_path / "DataFiles" / "scaled_0.expt").is_file()
        assert (tmp_path / "LogFiles" / "dials.scale.0.log").is_file()
    else:
        assert (tmp_path / "DataFiles" / "scaled.refl").is_file()
        assert (tmp_path / "DataFiles" / "scaled.expt").is_file()
        assert (tmp_path / "LogFiles" / "dials.scale.log").is_file()


def check_data_reduction_files_on_scaled_only(tmp_path, reference=False):
    assert (tmp_path / "data_reduction").is_dir()
    assert not (tmp_path / "data_reduction" / "prefilter").is_dir()
    assert not (tmp_path / "data_reduction" / "reindex").is_dir()
    assert not (tmp_path / "LogFiles" / "dials.cosym.0.log").is_file()
    assert not (tmp_path / "LogFiles" / "dials.cosym.0.html").is_file()
    assert (tmp_path / "data_reduction" / "scale").is_dir()
    assert (tmp_path / "data_reduction" / "scale" / "merged.mtz").is_file()
    assert (tmp_path / "DataFiles" / "merged.mtz").is_file()
    assert (tmp_path / "LogFiles" / "dials.merge.html").is_file()
    assert (tmp_path / "LogFiles" / "dials.merge.log").is_file()
    assert (tmp_path / "LogFiles" / "dials.merge.json").is_file()
    if reference:
        assert not (tmp_path / "DataFiles" / "scaled_0.refl").is_file()
        assert not (tmp_path / "DataFiles" / "scaled_0.expt").is_file()
        assert not (tmp_path / "LogFiles" / "dials.scale.0.log").is_file()
    else:
        assert (tmp_path / "DataFiles" / "scaled.refl").is_file()
        assert (tmp_path / "DataFiles" / "scaled.expt").is_file()
        assert (tmp_path / "LogFiles" / "dials.scale.log").is_file()


def check_data_reduction_files_on_scaled_plus_integrated(
    tmp_path, reindex=True, reference=False
):
    assert (tmp_path / "data_reduction").is_dir()
    assert (tmp_path / "data_reduction" / "prefilter").is_dir()
    assert reindex is (tmp_path / "data_reduction" / "reindex").is_dir()
    assert reindex is (tmp_path / "LogFiles" / "dials.cosym.0.log").is_file()
    assert reindex is (tmp_path / "LogFiles" / "dials.cosym.0.html").is_file()
    assert (tmp_path / "data_reduction" / "scale").is_dir()
    assert (tmp_path / "data_reduction" / "scale" / "merged.mtz").is_file()
    assert (tmp_path / "DataFiles" / "merged.mtz").is_file()
    assert (tmp_path / "LogFiles" / "dials.merge.html").is_file()
    assert (tmp_path / "LogFiles" / "dials.merge.log").is_file()
    if reference:
        assert (tmp_path / "DataFiles" / "scaled_0.refl").is_file()
        assert (tmp_path / "DataFiles" / "scaled_0.expt").is_file()
        assert (tmp_path / "LogFiles" / "dials.scale.0.log").is_file()
    else:
        assert (tmp_path / "DataFiles" / "scaled.refl").is_file()
        assert (tmp_path / "DataFiles" / "scaled.expt").is_file()
        assert (tmp_path / "LogFiles" / "dials.scale.log").is_file()


# For testing data reduction, there are a few different paths.
# Processing can be done on integrated data, only on previously scaled data,
# or on a mix of new data and previously scaled.
# Processing can be done with or without a reference pdb model
# There can be an indexing ambiguity or not

# With a reference - reindexing is done against this if idx ambiguity. New data is
# scaled. Any previously scaled data is merged in at the end.
# Without a reference - if idx ambiguity, unscaled input data is reindexed in
# batches, then all data (scaled plus unscaled) must be reindexed together in
# batch mode. Then all data is scaled together


@pytest.mark.parametrize(
    "pdb_model,idx_ambiguity",
    [(True, True), (True, False), (False, True), (False, False)],
)
def test_ssx_reduce(dials_data, tmp_path, pdb_model, idx_ambiguity):
    """Test ssx_reduce in the case of an indexing ambiguity or not.

    Test with and without a reference model, plus processing integrated,
    scaled, and integrated+scaled data.
    """
    ssx = dials_data("cunir_serial_processed", pathlib=True)
    if not idx_ambiguity:
        # Reindex to P432, which doesn't have an indexing ambiguity.
        result = subprocess.run(
            [
                "dials.reindex",
                f"{ssx / 'integrated.refl'}",
                f"{ssx / 'integrated.expt'}",
                "space_group=P432",
            ],
            cwd=tmp_path,
            capture_output=True,
        )
        assert not result.returncode and not result.stderr
        expts = tmp_path / "reindexed.expt"
        refls = tmp_path / "reindexed.refl"
        args = [
            "xia2.ssx_reduce",
            f"{refls}",
            f"{expts}",
        ]  # note - pass as files rather than directory to test that input option
    else:
        args = ["xia2.ssx_reduce", f"directory={ssx}"]
    extra_args = []
    if pdb_model:
        model = dials_data("cunir_serial", pathlib=True) / "2BW4.pdb"
        extra_args.append(f"model={str(model)}")
    # also test using scaling and cosym phil files
    cosym_phil = "d_min=2.5"
    scaling_phil = "reflection_selection.Isigma_range=3.0,0.0"
    with open(tmp_path / "scaling.phil", "w") as f:
        f.write(scaling_phil)
    with open(tmp_path / "cosym.phil", "w") as f:
        f.write(cosym_phil)
    extra_args.append("symmetry.phil=cosym.phil")
    extra_args.append("scaling.phil=scaling.phil")

    result = subprocess.run(args + extra_args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_data_reduction_files(tmp_path, reference=pdb_model, reindex=idx_ambiguity)

    # now run again only on previously scaled data
    pathlib.Path.mkdir(tmp_path / "reduce")
    args = [
        "xia2.ssx_reduce",
        f"processed_directory={tmp_path / 'DataFiles'}",
    ] + extra_args
    result = subprocess.run(args, cwd=tmp_path / "reduce", capture_output=True)
    assert not result.returncode and not result.stderr
    check_data_reduction_files_on_scaled_only(tmp_path / "reduce", reference=pdb_model)

    # now run again only on previously scaled data + integrated data
    # Need to assign new identifiers to avoid clash
    pathlib.Path.mkdir(tmp_path / "integrated_copy")
    if not idx_ambiguity:
        int_expts = load.experiment_list(
            tmp_path / "reindexed.expt", check_format=False
        )
        int_refls = flex.reflection_table.from_file(tmp_path / "reindexed.refl")
    else:
        int_expts = load.experiment_list(ssx / "integrated.expt", check_format=False)
        int_refls = flex.reflection_table.from_file(ssx / "integrated.refl")
    new_identifiers = ["0", "1", "2", "3", "4"]

    for i, (expt, new) in enumerate(zip(int_expts, new_identifiers)):
        expt.identifier = new
        del int_refls.experiment_identifiers()[i]
        int_refls.experiment_identifiers()[i] = new
    int_expts.as_file(tmp_path / "integrated_copy" / "integrated.expt")
    int_refls.as_file(tmp_path / "integrated_copy" / "integrated.refl")
    pathlib.Path.mkdir(tmp_path / "reduce_combined")
    args.append(f"directory={tmp_path / 'integrated_copy'}")
    result = subprocess.run(args, cwd=tmp_path / "reduce_combined", capture_output=True)
    assert not result.returncode and not result.stderr
    check_data_reduction_files_on_scaled_plus_integrated(
        tmp_path / "reduce_combined", reference=pdb_model, reindex=idx_ambiguity
    )


@pytest.mark.parametrize(
    ("cluster_args", "expected_results"),
    [
        (
            ["clustering.threshold=1"],
            {
                "best_unit_cell": [96.411, 96.411, 96.411, 90.0, 90.0, 90.0],
                "n_cryst": 3,
            },
        ),
        (
            [
                "central_unit_cell=96.4,96.4,96.4,90,90,90",
                "absolute_length_tolerance=0.015",
            ],
            {
                "best_unit_cell": [96.4107, 96.4107, 96.4107, 90.0, 90.0, 90.0],
                "n_cryst": 4,
            },
        ),
        (
            ["absolute_length_tolerance=0.001"],
            {
                "best_unit_cell": [96.4107, 96.4107, 96.4107, 90.0, 90.0, 90.0],
                "n_cryst": 2,
            },
        ),
    ],
)
def test_ssx_reduce_filter_options(
    dials_data, tmp_path, cluster_args: List[str], expected_results: dict
):
    ssx = dials_data("cunir_serial_processed", pathlib=True)
    args = ["xia2.ssx_reduce", f"directory={ssx}"] + cluster_args

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_data_reduction_files(tmp_path)

    expts = load.experiment_list(tmp_path / "DataFiles" / "scaled.expt")
    assert len(expts) == expected_results["n_cryst"]

    assert list(determine_best_unit_cell(expts).parameters()) == pytest.approx(
        expected_results["best_unit_cell"]
    )


def test_on_sacla_data(dials_data, tmp_path):

    sacla_path = dials_data("image_examples", pathlib=True)
    image = sacla_path / "SACLA-MPCCD-run266702-0-subset.h5"
    # NB need to set gain, as using reference from detector overwrites gain to 1
    # error with reference geom file? Alt is to manually set detector distance in
    # import.
    find_spots_phil = """spotfinder.threshold.dispersion.gain=10"""
    fp = tmp_path / "sf.phil"
    with open(fp, "w") as f:
        f.write(find_spots_phil)
    geometry = (
        sacla_path / "SACLA-MPCCD-run266702-0-subset-refined_experiments_level1.json"
    )
    args = [
        "xia2.ssx",
        f"image={image}",
        f"reference_geometry={geometry}",
        "space_group = P43212",
        "unit_cell=78.9,78.9,38.1,90,90,90",
        "min_spot_size=2",
        "integration.algorithm=stills",
        f"spotfinding.phil={fp}",
    ]
    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(tmp_path, find_spots=True, index=True, integrate=True)

    imported = load.experiment_list(
        tmp_path / "import" / "imported.expt", check_format=False
    )
    assert len(imported) == 4
    assert len(imported.imagesets()) == 1
    assert (tmp_path / "DataFiles" / "merged.mtz").is_file()
