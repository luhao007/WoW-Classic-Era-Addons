import json
import os
from pathlib import Path

import instawow.cli
from instawow.config import Config
from instawow.models import Pkg
from instawow.resolvers import Defn, MultiPkgModel
from instawow.results import PkgUpToDate


class InstawowManager:

    def __init__(self, ctx, game_flavour, lib=False):
        """Interface between instawow and main program.

        :param game_flavor str: 'classic' or 'retail' or 'vanilla_classic'
        :param lib bool: Whether hanlding libraries.
        :param lib classic_only_lib: Whether hanlding classic-only libs
        """
        self.profile = game_flavour + ('_lib' if lib else '')
        ctx.params['profile'] = self.profile

        addon_dir = Path(os.getcwd()) / 'Addons/'
        if lib:
            addon_dir /= '!!Libs'
        config = Config(addon_dir=addon_dir, game_flavour=game_flavour, profile=self.profile)
        config.write()

        self.manager = instawow.cli.ManagerWrapper(ctx).m

    def get_addons(self):
        query = self.manager.database.query(Pkg)
        return query.order_by(Pkg.source, Pkg.name).all()

    def update(self):
        addons = [Defn.from_pkg(p) for p in self.get_addons()]
        results = self.manager.run(self.manager.update(addons, False))
        report = instawow.cli.Report(results.items(),
                                     lambda r: not isinstance(r, PkgUpToDate))
        if str(report):
            print(report)
        else:
            print('All {} addons are up-to-date!'.format(self.profile))

    def install(self, addons, strategy=None):
        addons = instawow.cli.parse_into_defn(self.manager, addons)
        if isinstance(addons, Defn):
            addons = [addons]
        if '_lib' in self.profile:
            addons = [Defn.with_strategy(d, 'any_flavour') for d in addons]
        elif strategy:
            addons = [Defn.with_strategy(d, strategy) for d in addons]
        results = self.manager.run(self.manager.install(addons, replace=False))
        print(instawow.cli.Report(results.items()))

    def remove(self, addons):
        addons = instawow.cli.parse_into_defn(self.manager, addons)
        if isinstance(addons, Defn):
            addons = [addons]
        results = self.manager.run(self.manager.remove(addons, False))
        print(instawow.cli.Report(results.items()))

    def show(self):
        for addon in self.get_addons():
            print('{}: {}'.format(addon.name, addon.version))

    def export(self):
        with open(f'{self.profile}.json', 'w') as f:
            f.write(MultiPkgModel.parse_obj(self.get_addons()).json(indent=2))

    def reinstall(self, file):
        with open(file, 'rb') as f:
            l = json.loads(f.read())
        addons = [(a['options']['strategy'], f"{a['source']}:{a['slug']}") for a in l]
        addons = list(instawow.cli.parse_into_defn_with_strategy(self.manager, addons))
        results = self.manager.run(self.manager.install(addons, replace=True))
        print(instawow.cli.Report(results.items()))