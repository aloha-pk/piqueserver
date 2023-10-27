import zlib
import threading

COMPRESSION_LEVEL = 9

class MapCache:
    def __init__(self, max_maps=1):
        self.cache = {}
        self.max_maps = max_maps

    def add_map(self, map_hash, map_data):
        if len(self.cache) >= self.max_maps:
            oldest_map_hash = list(self.cache.keys())[0]
            del self.cache[oldest_map_hash]
        
        self.cache[map_hash] = map_data

    def get_map(self, map_hash):
        return self.cache.get(map_hash)

    def has_map(self, map_hash):
        return map_hash in self.cache
    
    def reset_cache(self):
        self.cache.clear()

# Global cache instance
map_cache = MapCache(max_maps=1)


class ProgressiveMapGenerator:
    data = b''
    done = False

    # parent attributes
    all_data = b''
    pos = 0

    def __init__(self, map_, parent=False):
        self.parent = parent
        self.generator = map_.get_generator()
        self.compressor = zlib.compressobj(COMPRESSION_LEVEL)
        self.lock = threading.Lock()
        self.data_ready = threading.Condition(self.lock)
        self.is_generating = False

    def get_size(self):
        return 1.5 * 1024 * 1024  # 2MB

    def read(self, size):
        with self.lock:
            if len(self.data) < size and self.generator:
                if self.is_generating:
                    self.data_ready.wait()
                else:
                    self.is_generating = True
                    thread = threading.Thread(target=self._generate_and_compress_map, args=(size,))
                    thread.start()
                    self.data_ready.wait()
                    self.is_generating = False

            data_to_return = self.data[:size]
            self.data = self.data[size:]

            if self.parent:
                self.all_data += data_to_return
                self.pos += len(data_to_return)

            return data_to_return

    def _generate_and_compress_map(self, size):
        data = b''
        while len(data) < size and self.generator:
            map_data = self.generator.get_data(size)
            if self.generator.done:
                data += self.compressor.flush()
                self.generator = None
            else:
                data += self.compressor.compress(map_data)

        with self.lock:
            self.data += data
            self.data_ready.notify_all()

    def get_child(self):
        if self.parent:
            return MapGeneratorChild(self)
        else:
            raise NotImplementedError("get_child is not implemented for non-parent generators")

    def data_left(self):
        return bool(self.data) or self.generator is not None


class MapGeneratorChild:
    pos = 0

    def __init__(self, generator):
        self.parent = generator

    def get_size(self):
        return self.parent.get_size()

    def read(self, size):
        pos = self.pos
        if pos + size > self.parent.pos:
            self.parent.read(size)
        data = self.parent.all_data[pos:pos + size]
        self.pos += len(data)
        return data

    def data_left(self):
        return self.parent.data_left() or self.pos < self.parent.pos
