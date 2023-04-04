# -*- coding: utf-8 -*-

import click
import yaml

from rompy.swan import SwanModel


@click.command()
@click.argument("config", type=click.File("r"))
@click.option(
    "--kwargs",
    "-k",
    multiple=True,
    help="additional key value pairs in the format key:value",
)
def main(config, kwargs):
    """Run model
    Usage: swan config.yml
    Args:
        config(str): yaml config file
    """
    args = yaml.load(config, Loader=yaml.Loader)

    kw = {}
    for item in kwargs:
        split = item.split(":")
        kw.update({split[0]: split[1]})
        current = getattr(instance, split[0])
        setattr(instance, split[0], type(current)(split[1]))
    model = SwanModel(**args)
    model()


if __name__ == "__main__":
    main()
