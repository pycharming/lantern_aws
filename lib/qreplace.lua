-- KEYS[1]: name of the queue to use
-- ARGV[1]: name of the old item
-- ARGV[2]: name of the new item

redis.call("lrem", KEYS[1], 1, ARGV[1])
redis.call("lpush", KEYS[1], ARGV[2])
return ARGV[1]
