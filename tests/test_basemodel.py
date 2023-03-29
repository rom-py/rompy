import pytest

from rompy.core import BaseModel


def compare_files(file1, file2):
    with open(file1, "r") as f1:
        with open(file2, "r") as f2:
            for line1, line2 in zip(f1, f2):
                if line1[0] != "$" and line2[0] != "$":
                    assert line1 == line2


@pytest.fixture
def model():
    return BaseModel(run_id="test_base", output_dir="simulations")


# test generate method
def test_generate(model):
    model.generate()
    compare_files("simulations/test_base/INPUT", "simulations/test_base_ref/INPUT")
