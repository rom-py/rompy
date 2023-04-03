import os
import tempfile

import pytest

from rompy.data import DataPath


# create dummy local datasource for testing
@pytest.fixture
def txt_data_source():
    # touch temp text file
    tmp_path = tempfile.mkdtemp()
    source = os.path.join(tmp_path, "test.txt")
    with open(source, "w") as f:
        f.write("hello world")
    return DataPath(path=source)


def test_stage(txt_data_source):
    ds = txt_data_source
    output = ds.stage("./test.txt")
    assert output.path.is_file()
