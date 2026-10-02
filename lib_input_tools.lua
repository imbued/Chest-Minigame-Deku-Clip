itools = {}

local core = dofile('lib_core.lua')

local version = core.version
if(version == 0) then
   -- english
   itools.vframe_addr = 0x1f9f80
elseif(version == 1) then
   -- jp 1.0
   itools.vframe_addr = 0x1fa0f0
elseif(version == 2) then
   -- jp 1.1
   itools.vframe_addr = 0x1fa3a0
else
   -- error
   core.printf('Unknown ROM')
   return
end

function itools.load_state(state, allow_inc)
   --- Generic wrapper for the loadslot and load named savestate Bizhawk functions.
   --- If state is a number, it loads the numbered savestate.
   --- Otherwise, it will try to load the save state with the matching name.
   --- allow_inc is an optional binary value for if the re-record count of a movie could be incremented or not.
   ---
   --- The rerecord count will only be incremented if the movie is currently in read/write mode.
   
   if(allow_inc == nil or allow_inc == true) then
      if(movie.isloaded()) then
         if(not movie.getreadonly() and movie.getrerecordcounting()) then
            movie.setrerecordcount(movie.getrerecordcount() + 1)
         end
      end
   end
   if(type(state) == type(1)) then
      -- load number slot
      savestate.loadslot(state)
   else
      -- load named slot
      savestate.load(state)
   end
end

function itools.save_state(state)
   --- Generic wrapper for the saveslot and svae named savestate Bizhawk functions.
   --- If state is a number, it saves the numbered savestate.
   --- Otherwise, it will try to save the save state as a given name.
   
   if(type(state) == type(1)) then
      -- save number slot
      savestate.saveslot(state)
   else
      -- save named slot
      savestate.save(state)
   end
end

function itools.clear_inputs(controller)
   --- Helper for unpressing all buttons and moving the analog stick to neutral
   --- @param controller optional integer parameter for the given controller number
   --- (default is for controller 1)
   
   if(controller == nil) then
      controller = 1
   end
   dict = {["A"]=false,["B"]=false,
      ["C Down"]=false,["C Left"]=false,["C Right"]=false,["C Up"]=false,
      ["DPad D"]=false,["DPad L"]=false,["DPad R"]=false,["DPad U"]=false,
      ["L"]=false,["R"]=false,
      ["Start"]=false,
      ["Z"]=false,
      ["X Axis"] = 0, ["Y Axis"] = 0}
   joypad.set(dict,controller)
   joypad.setanalog(dict,controller)
end

function itools.do_inputs(input_list, controller)
   --- Helper function for running a sequence of inputs on sequential input frames
   --- @param controller optional integer parameter for the given controller number
   --- (default is for controller 1)
   
   if(controller == nil) then
      controller = 1
   end
   for i,dict in ipairs(input_list) do
      itools.clear_inputs(controller)
      if(dict['Power'] ~= nil) then
         joypad.set(dict)
      end
      joypad.set(dict,1)
      joypad.setanalog(dict,1)
      emu.frameadvance()
   end
end

function itools.print_inputs(input_list, controller)
   --- Helper for printing out a given input list which can be passed to do_input.
   --- Mostly for debugging purposes.
   for i,dict in ipairs(input_list) do
      print(i,dict)
   end
end

function itools.iframe_advance(input_state, controller, pause)
   --- Helper which wraps setting the current controller state, as well as advances an input frame
   --- @param controller optional integer parameter for the given controller number
   --- (default is for controller 1)
   --- @param pause Optional parameter when true will pause the emulator at the end of the function
   
   if(controller == nil) then
      controller = 1
   end
   if(pause == nil) then
      pause = false
   end
   if(input_state ~= nil) then
      joypad.set(input_state, controller)
      joypad.setanalog(input_state, controller)
   end
   emu.frameadvance()
   if(pause == true) then
      client.pause()
   end
end

function itools.vframe_advance(input_state, controller, pause, max_frames)
   --- Helper which wraps setting the current controller state, as well as advances to the start of the next visual frame. Note that this will skip past "lag frames" as well, so it doesn't
   --- matter if there are a few lag frames. There are other times which are classified by "lag frames" (load zones, I think bringing up the pause menu?)
   --- In order to not skip past these, you can use the max_frames parameter.
   --- @param input_state What buttons/analog position should be held for the duration of the current input frame
   --- @param controller optional integer parameter for the given controller number
   --- (default is for controller 1)
   --- @param pause Optional parameter when true will pause the emulator at the end of the function
   --- @param max_frames maximum number of input frames to skip past.
   if(controller == nil) then
      controller = 1
   end
   if(pause == nil) then
      pause = false
   end
   if(max_frames == nil) then
      max_frames = 300
   end
   local addr = itools.vframe_addr
      
   local last_vframe = memory.read_u32_be(addr, 'RDRAM')
   local iter = 0
   repeat
      if(input_state ~= nil) then
         joypad.set(input_state, controller)
         joypad.setanalog(input_state, controller)
      end
      iter = iter + 1
      emu.frameadvance()
   until(last_vframe ~= memory.read_u32_be(addr, 'RDRAM') or iter > max_frames)
   if(pause == true) then
      client.pause()
   end
end

return itools
