"""
This module implements different plugins you can attach to your cache instance. They
are coded in a collaborative so you can use multiple inheritance.
"""

from pylav.vendored.aiocache.base import API


class BasePlugin:
    @classmethod
    def add_hook(cls, func, hooks):
        for hook in hooks:
            setattr(cls, hook, func)

    async def do_nothing(self, *args, **kwargs):
        pass


BasePlugin.add_hook(BasePlugin.do_nothing, [f"pre_{method.__name__}" for method in API.CMDS])
BasePlugin.add_hook(BasePlugin.do_nothing, [f"post_{method.__name__}" for method in API.CMDS])


class TimingPlugin(BasePlugin):
    """
    Calculates average, min and max times each command takes. The data is saved
    in the cache class as a dict attribute called ``profiling``. For example, to
    access the average time of the operation get, you can do ``cache.profiling['get_avg']``
    """

    @classmethod
    def save_time(cls, method):
        async def do_save_time(self, client, *args, took=0, **kwargs):
            if not hasattr(client, "profiling"):
                client.profiling = {}

            previous_total = client.profiling.get(f"{method}_total", 0)
            previous_avg = client.profiling.get(f"{method}_avg", 0)
            previous_max = client.profiling.get(f"{method}_max", 0)
            previous_min = client.profiling.get(f"{method}_min")

            client.profiling[f"{method}_total"] = previous_total + 1
            client.profiling[f"{method}_avg"] = previous_avg + (took - previous_avg) / (previous_total + 1)
            client.profiling[f"{method}_max"] = max(took, previous_max)
            client.profiling[f"{method}_min"] = min(took, previous_min) if previous_min else took

        return do_save_time


for method in API.CMDS:
    TimingPlugin.add_hook(TimingPlugin.save_time(method.__name__), [f"post_{method.__name__}"])


class HitMissRatioPlugin(BasePlugin):
    """
    Calculates the ratio of hits the cache has. The data is saved in the cache class as a dict
    attribute called ``hit_miss_ratio``. For example, to access the hit ratio of the cache,
    you can do ``cache.hit_miss_ratio['hit_ratio']``. It also provides the "total" and "hits"
    keys.
    """

    async def post_get(self, client, key, took=0, ret=None, **kwargs):
        if not hasattr(client, "hit_miss_ratio"):
            client.hit_miss_ratio = {}
            client.hit_miss_ratio["total"] = 0
            client.hit_miss_ratio["hits"] = 0

        client.hit_miss_ratio["total"] += 1
        if ret is not None:
            client.hit_miss_ratio["hits"] += 1

        client.hit_miss_ratio["hit_ratio"] = client.hit_miss_ratio["hits"] / client.hit_miss_ratio["total"]

    async def post_multi_get(self, client, keys, took=0, ret=None, **kwargs):
        if not hasattr(client, "hit_miss_ratio"):
            client.hit_miss_ratio = {}
            client.hit_miss_ratio["total"] = 0
            client.hit_miss_ratio["hits"] = 0

        client.hit_miss_ratio["total"] += len(keys)
        for result in ret:
            if result is not None:
                client.hit_miss_ratio["hits"] += 1

        client.hit_miss_ratio["hit_ratio"] = client.hit_miss_ratio["hits"] / client.hit_miss_ratio["total"]
