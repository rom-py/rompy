import os
import tempfile

import pytest

from rompy.data import DataBlob, DataGrid


# create dummy local datasource for testing
@pytest.fixture
def txt_data_source():
    # touch temp text file
    tmp_path = tempfile.mkdtemp()
    source = os.path.join(tmp_path, "test.txt")
    with open(source, "w") as f:
        f.write("hello world")
    return DataBlob(path=source)


def test_stage(txt_data_source):
    ds = txt_data_source
    output = ds.stage("./test.txt")
    assert output.path.is_file()


def test_stage_no_path(txt_data_source):
    ds = txt_data_source
    with pytest.raises(TypeError):
        ds.stage()


def test_fails_both_path_and_url():
    with pytest.raises(ValueError):
        DataBlob(path="foo", url="bar")


# @pytest.fixture
# def grid_data_source():
#     return DataBlob(
#         url="https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/gfs.20210501/00/atmos/gfs.t00z.pgrb2.0p25.f000"
#     )
#
#
# def test_grid_stage(grid_data_source):
#     ds = grid_data_source
#     output = ds.stage("./test.nc")
#     assert output.path.is_file()
