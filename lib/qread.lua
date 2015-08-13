-- KEYS[1]: name of the queue to use.
-- ARGV[1]: current unix timestamp.

local item = redis.call("rpop", KEYS[1])
if string.find(item, "*") then
  redis.call("lpush", KEYS[1], item)
else
  redis.call("lpush", KEYS[1], item .. "*" .. ARGV[1])
end
return item
