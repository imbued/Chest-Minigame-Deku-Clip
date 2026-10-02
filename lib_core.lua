core = {}

-- ROM's game version
-- nil: unknown
-- 0: EN
-- 1: JP 1.0
-- 2: JP 1.1
local code = memory.read_u16_be(0x3E, 'ROM')
if(code == 0x4A00) then
   core.version = 1
elseif(code == 0x4A01) then
   core.version = 2
elseif(code == 0x4500) then
   core.version = 0
end

function core.concat_lists(list_a, list_b)
   -- concatenates list b to list a (new list)
   -- return concatenated list
   local res = {}
   for i,v in ipairs(list_a) do
      res[i] = v
   end
   for i,v in ipairs(list_b) do
      table.insert(res, v)
   end
   return res
end

function core.read_float_be(addr, memspace)
   --- Wrapper around memory.readfloat so it's interface is the same as all the other
   --- memory reading functions.
   return memory.readfloat(addr, true, memspace)
end

function core.write_float_be(addr, v, memspace)
   --- Wrapper around memory.writefloat so it's interface is the same as all the other
   --- memory reading functions.
   memory.writefloat(addr, v, true, memspace)
end

function core.printf(fmt, ...)
   --- Simple print function which essentially does what printf in other languages does
   print(fmt:format(...))
end

return core
