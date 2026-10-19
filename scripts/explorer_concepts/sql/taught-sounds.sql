SELECT DISTINCT value FROM concepts, json_each(concepts.sounds) WHERE kind = 'phonogram'
