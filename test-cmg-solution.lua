itools = dofile('lib_input_tools.lua')
core = dofile('lib_core.lua')

addresses = {
    {
        ["name"] = "Angle",
        ["address"] = 0x3FFE6E,
        ["size"] = 2,
        ["type"] = "hex",
    },

    {
        ["name"] = "Camera Angle",
        ["address"] = 0x3E6E7C,
        ["size"] = 2,
        ["type"] = "hex",
    },

    {
        ["name"] = "Movement Angle",
        ["address"] = 0x400884,
        ["size"] = 2,
        ["type"] = "hex",
    },

    {
        ["name"] = "Linear Velocity",
        ["address"] = 0x400880,
        ["size"] = 4,
        ["type"] = "float",
    },

    {
        ["name"] = "X Velocity",
        ["address"] = 0x3FFE14,
        ["size"] = 4,
        ["type"] = "float",
    },

    {
        ["name"] = "Y Velocity",
        ["address"] = 0x3FFE18,
        ["size"] = 4,
        ["type"] = "float",
    },

    {
        ["name"] = "Z Velocity",
        ["address"] = 0x3FFE1C,
        ["size"] = 4,
        ["type"] = "float",
    },

    {
        ["name"] = "X Position",
        ["address"] = 0x3FFDD4,
        ["size"] = 4,
        ["type"] = "float",
    },

    {
        ["name"] = "Y Position",
        ["address"] = 0x3FFDD8,
        ["size"] = 4,
        ["type"] = "float",
    },

    {
        ["name"] = "Z Position",
        ["address"] = 0x3FFDDC,
        ["size"] = 4,
        ["type"] = "float",
    },

    {
        ["name"] = "Vertical Camera Angle",
        ["address"] = 0x3E6E7A,
        ["size"] = 2,
        ["type"] = "hex",
    },
}

mem = {}
for _, entry in ipairs(addresses) do
    mem[entry["name"]] = entry["address"]
end



function read_memory(entry)
    --- Read a value from RDRAM according to the specification in `entry`.
    ---
    --- `entry` should be a table with:
    ---   ["address"]: memory address
    ---   ["size"]: number of bytes to read (1, 2, or 4)
    ---   ["type"]: how to interpret the value ("float" or "hex")
    ---
    --- Example:
    ---   addresses = {
    ---       ["Angle"] = {
    ---           ["address"] = 0x3FFE6E,
    ---           ["size"] = 2,
    ---           ["type"] = "hex",
    ---       },
    ---   }
    ---
    ---   local angle = read_memory(addresses["Angle"])

    if entry["type"] == "float" then
        return core.read_float_be(entry["address"], "RDRAM")
    end

    if entry["type"] == "hex" then
        if entry["size"] == 1 then
            return memory.read_u8(entry["address"], "RDRAM")
        elseif entry["size"] == 2 then
            return memory.read_u16_be(entry["address"], "RDRAM")
        elseif entry["size"] == 4 then
            return memory.read_u32_be(entry["address"], "RDRAM")
        end
    end
end

function v_advance(amount, inputs, addresses)
    --- Advance `amount` visual frames while holding the specified inputs.
    ---
    --- `amount`: number of visual frames to advance
    --- `inputs`: optional table specifying buttons/analog inputs
    --- `addresses`: optional table of named memory addresses to read after each frame
    ---
    --- If `addresses` is provided, returns a table where:
    ---   values[frame][name] = value read from the corresponding address
    ---
    --- Example without reading memory:
    ---   v_advance(10, {["A"] = true})
    ---
    --- Example with memory reads:
    ---   local values = v_advance(
    ---       100,
    ---       {["Z"] = true, ["X Axis"] = -128, ["Y Axis"] = 0},
    ---       addresses
    ---   )
    ---
    ---   local angle = values[1]["Angle"]
    ---   local x_position = values[50]["X Position"]
    itools.clear_inputs() -- clear inputs before doing anything to ensure only the current inputs occur
    local values = nil

    if addresses then
        values = {}
    end

    for frame = 1, amount do
        itools.vframe_advance(inputs)

        if addresses then
            values[frame] = {}

            for _, entry in ipairs(addresses) do
                values[frame][entry["name"]] = read_memory(entry)
            end
        end
    end
    itools.clear_inputs() -- clear inputs at the very end just out of caution
    return values
end

function append_values(values, new_values)
    if new_values then
        for _, value in ipairs(new_values) do
            table.insert(values, value)
        end
    end
end

function hold_sidehop(left, addresses)
    --- Note: this is specifically a deku hold sidehop, this may not work for other forms
    --- `left` is a boolean, if true then sidehop left if false then sidehop right
    local control_stick
    if left then
        control_stick = -128
    else
        control_stick = 127
    end

    local values = {}
    -- hold target for at least 6 frames before doing anything else
    append_values(values, v_advance(
        6,
        {["Z"] = true},
        addresses
    ))
    -- press A and hold the control stick for 1 frame
    append_values(values, v_advance(
        1,
        {["Z"] = true, ["A"] = true, ["X Axis"] = control_stick},
        addresses
    ))
    -- start holding shield midair so you won't move after landing
    append_values(values, v_advance(
        7,
        {["Z"] = true, ["R"] = true, ["X Axis"] = control_stick},
        addresses
    ))

    return values
end

function hold_backflip(addresses)
    --- Note: this is specifically a deku hold backflip, this may not work for other forms
    local control_stick
    control_stick = -128

    local values = {}
    -- hold target for at least 6 frames before doing anything else
    append_values(values, v_advance(
        6,
        {["Z"] = true},
        addresses
    ))
    append_values(values, v_advance(
        1,
        {["Z"] = true, ["A"] = true, ["Y Axis"] = control_stick},
        addresses
    ))
    append_values(values, v_advance(
        12,
        {["Z"] = true, ["R"] = true, ["Y Axis"] = control_stick},
        addresses
    ))

    return values
end

--- edit: I feel like holding target vs not holding target is kinda fake? like seems to not really matter? though i didn't inspect the data super heavily
-- function hold_deku_spin(target, addresses)
--     --- `target` is a boolean, True if we hold target while holding up and pressing A, False other
--     local control_stick
--     control_stick = 127

--     local values = {}
--     -- hold target for at least 6 frames before doing anything else
--     append_values(values, v_advance(
--         6,
--         {["Z"] = true},
--         addresses
--     ))
--     append_values(values, v_advance(
--         1,
--         {["Z"] = target, ["A"] = true, ["Y Axis"] = control_stick},
--         addresses
--     ))
--     append_values(values, v_advance(
--         20,
--         {["Z"] = target, ["R"] = true, ["Y Axis"] = control_stick},
--         addresses
--     ))

--     return values
-- end


function hold_deku_spin(direction, turn_first, addresses)
    --- `direction` is "left", "right", "down", "up". If "down", then `turn_first` MUST be true. if "up" then `turn_first` MUST be false.
    --- `turn_first` is a boolean, if True we e..g tap left to turn (but do NOT target) before doing the spin. this give a bit of a different spin trajectory
    local control_stick
    if direction == "right" or direction == "up" then
        control_stick = 127
    elseif direction == "left" or direction == "down" then
        control_stick = -128
    else
        assert(false, "this should be impossible")
    end

    if direction == "down" then
        assert(turn_first == true, "`turn_first` must be true if going down")
    end
    if direction == "up" then
        assert(turn_first == false, "`turn_first` must be false if going up")
    end

    if direction == "up" or direction == "down" then
        axis = "Y Axis"
    elseif direction == "left" or direction == "right" then
        axis = "X Axis"
    else
        assert(false, "this should be impossible!")
    end

    local values = {}
    append_values(values, target_and_untarget_and_let_camera_snap(addresses)) -- let's camera snap to e.g. cardinal angle if applicable
    if turn_first then
        append_values(values, v_advance(1, {[axis] = control_stick}, addresses))
    end

    append_values(values, v_advance(
        1,
        {["A"] = true, [axis] = control_stick},
        addresses
    ))
    append_values(values, v_advance(
        20,
        {["R"] = true, [axis] = control_stick},
        addresses
    ))

    return values
end


function guanowalk(left, addresses)
    --- `left` is a boolean, if true then sidehop left if false then sidehop right
    --- WARNING: if a left/right guanowalk doesn't move you forward, it takes 1 extra frame for your velocity to be nonzero, so guano shield scoots can have different timings depending on your angle/camera angle
    --- SINCE I THINK I LOOKED AT THE SAME FRAME EVERY TIME
    local control_stick
    if left then
        control_stick = -128
    else
        control_stick = 127
    end

    local values = {}
    -- hold target for at least 6 frames before doing anything else
    append_values(values, v_advance(
        6,
        {["Z"] = true},
        addresses
    ))
    append_values(values, v_advance(
        32,
        {["Z"] = true, ["X Axis"] = control_stick},
        addresses
    ))

    return values
end

function get_address(name) -- this is so stupid, but whatever
    for _, entry in ipairs(addresses) do
        if entry["name"] == name then
            return entry
        end
    end
end
function guano_shield_scoot(left, reset_chain, addresses)
    --- `left` is a boolean, if true then sidehop left if false then sidehop right
    --- `reset_chain` is a boolean, if true then we do an unshielded target at the start to reset the movement angle
    local control_stick
    if left then
        control_stick = -128
    else
        control_stick = 127
    end

    local values = {}
    -- if you release shield, after the guano scoot w/o guano scooting again, it'll reset the stored movement angle which is needed for the guano shield scoot chain
    if reset_chain then
        append_values(values, v_advance(
            6,
            {},
            addresses
        ))
        append_values(values, v_advance(
            6,
            {["Z"] = true},
            addresses
        ))
    end

    append_values(values, v_advance(
        10,
        {["Z"] = true, ["R"] = true, ["X Axis"] = control_stick},
        addresses
    ))
    -- depending on camera angle, it can take an extra frame to begin movement, so we need to do this while loop checking linear velocity
    local v
    v = read_memory(get_address("Linear Velocity"))
    while v == 0 do
        append_values(values, v_advance(
            1,
            {["Z"] = true, ["X Axis"] = control_stick},
            addresses
        ))
        v = read_memory(get_address("Linear Velocity"))
    end

    append_values(values, v_advance(
        3,
        {["Z"] = true, ["R"] = true, ["X Axis"] = control_stick},
        addresses
    ))

    append_values(values, v_advance(
        1,
        {["Z"] = true, ["R"] = true},
        addresses
    ))


    return values
end


function shield_scoot_forward(addresses)
    --- note that I always do the forward shield scoot while TARGETED!!
    local control_stick
    control_stick = 127

    local values = {}
    -- if you release shield, after the guano scoot w/o guano scooting again, it'll reset the stored movement angle which is needed for the guano shield scoot chain

    append_values(values, v_advance(
        10,
        {["Z"] = true, ["R"] = true, ["Y Axis"] = control_stick},
        addresses
    ))

    append_values(values, v_advance(
        3,
        {["Z"] = true, ["Y Axis"] = control_stick},
        addresses
    ))

    append_values(values, v_advance(
        3,
        {["Z"] = true, ["R"] = true, ["Y Axis"] = control_stick},
        addresses
    ))

    append_values(values, v_advance(
        1,
        {["Z"] = true, ["R"] = true},
        addresses
    ))


    return values
end

function target_and_untarget_and_let_camera_snap(addresses)
    --- we want to target, then untarget and wait for the camera angle to settle (important because some camera angle snap to cardinal directions)
    local values = {}
    -- hold target for at least 6 frames before doing anything else
    append_values(values, v_advance(
        6,
        {["Z"] = true},
        addresses
    ))
    local old_cam
    local new_cam
    old_cam = read_memory(get_address("Camera Angle"))
    append_values(values, v_advance(
        10,
        {},
        addresses
    ))
    new_cam = read_memory(get_address("Camera Angle"))
    while old_cam ~= new_cam do
        append_values(values, v_advance(
            10,
            {},
            addresses
        ))
        old_cam = new_cam
        new_cam = read_memory(get_address("Camera Angle"))
    end
    
    return values
end


function cardinal_turn(direction, addresses)
    --- `left` is a boolean, if true then sidehop left if false then sidehop right
    local values = {}
    -- hold target for at least 6 frames before doing anything else
    append_values(values, target_and_untarget_and_let_camera_snap(addresses)) -- let's camera snap to e.g. cardinal angle if applicable
    append_values(values, v_advance(
        1,
        {},
        addresses
    ))
    hold_length = 1
    if direction == "LEFT" then
        append_values(values, v_advance(
            hold_length,
            {["X Axis"] = -128},
            addresses
        ))
    elseif direction == "RIGHT" then
        append_values(values, v_advance(
            hold_length,
            {["X Axis"] = 127},
            addresses
        ))
    elseif direction == "DOWN" then
        append_values(values, v_advance(
            hold_length,
            {["Y Axis"] = -128},
            addresses
        ))
    elseif direction == "UP" then
        append_values(values, v_advance(
            hold_length,
            {["Y Axis"] = 127},
            addresses
        ))
    end
    -- target at the very end just to set up nicely for any future movements outside of the context of this function
    append_values(values, v_advance(
        6,
        {["Z"] = true},
        addresses
    ))
    return values
end


function ess_turn(left, num_turns, addresses)
    --- `left` is a boolean, if true then sidehop left if false then sidehop right
    local control_stick
    if left then
        control_stick = -20
    else
        control_stick = 20
    end

    local values = {}
    -- hold target for at least 6 frames before doing anything else
    append_values(values, v_advance(
        6,
        {["Z"] = true},
        addresses
    ))
    append_values(values, v_advance(
        6,
        {},
        addresses
    ))
    if num_turns <= 9 then
        append_values(values, v_advance(
            num_turns + 1,
            {["X Axis"] = control_stick},
            addresses
        ))
    else
        for i = 1, num_turns, 1 do -- do 1 ess turn as a time and target after every one if doing >9 turns to avoid snapping to camera angle
        append_values(values, v_advance(
            2, -- 2 frames does 1 ess turn
            {["X Axis"] = control_stick},
            addresses
        ))
        append_values(values, v_advance(
            6,
            {["Z"] = true},
            addresses
        ))
        end
    end
    return values
end


-- function deku_spin_in_place(left, addresses)
--     --- `left` is a boolean, if true then sidehop left if false then sidehop right
--     local control_stick
--     if left then
--         control_stick = -128
--     else
--         control_stick = 127
--     end

--     local values = {}
--     -- hold target for at least 6 frames before doing anything else
--     append_values(values, v_advance(
--         6,
--         {["Z"] = true},
--         addresses
--     ))
--     append_values(values, v_advance(
--         22, -- 21 is prob sufficient, just being safe
--         {["A"] = true},
--         addresses
--     ))
--     append_values(values, v_advance( -- targeting to setup nicely for other movements, just to be safe
--         6,
--         {["Z"] = true},
--         addresses
--     ))
--     return values
-- end

function deku_spin_in_place(num_spins, addresses)
    local values = {}
    append_values(values, v_advance(
            30, -- idk how big this needs to be, but didn't have this before and got issues with spin in place after hold backflip
            {},
            addresses
        ))
    for i = 1, num_spins do
        append_values(values, v_advance(
            6,
            {["Z"] = true},
            addresses
        ))

        append_values(values, v_advance(
            22,
            {["A"] = true},
            addresses
        ))
    end
    append_values(values, v_advance(
        6,
        {["Z"] = true},
        addresses
    ))
    return values
end





function initialize_csv(filename, addresses)
    local file = io.open(filename, "w")

    file:write("Initial Angle,Frame")

    for _, entry in ipairs(addresses) do
        file:write("," .. entry["name"])
    end

    file:write("\n")
    file:close()
end

function append_values_to_csv(filename, values, addresses, initial_angle)
    local file = io.open(filename, "a")

    local initial_angle_string = string.format("0x%04X", initial_angle)

    for frame, frame_values in ipairs(values) do
        file:write(initial_angle_string .. "," .. frame)

        for _, entry in ipairs(addresses) do
            local value = frame_values[entry["name"]]

            if entry["type"] == "hex" then
                local hex_digits = entry["size"] * 2
                value = string.format("0x%0" .. hex_digits .. "X", value)
            end

            file:write("," .. tostring(value))
        end

        file:write("\n")
    end

    file:close()
end







-- function parse_movements(filename)
--     local movements = {}

--     for line in io.lines(filename) do
--         if line:match("^%s+") and line:find("%(X, Z, Angle, Cam%)") then
--             -- local movement = line:match("^%s*(.-)%s+%(")
--             local movement = line:match("^%s*(.-)%s+%(")
--             movement = movement:match("^(.-)%s*%[") or movement

--             -- Numeric argument, e.g. "-8 ESS Turns" or "5 ESS Turns"
--             local number, action = movement:match("^([%-]?%d+)%s+(.+)$")

--             if number then
--                 table.insert(movements, {
--                     action = action,
--                     argument = tonumber(number),
--                 })
--             else
--                 -- Cardinal Turn argument, e.g. "Cardinal Turn RIGHT"
--                 local action, argument = movement:match("^(.-)%s+(%S+)$")

--                 if argument == "LEFT" or argument == "RIGHT" or argument == "DOWN" then
--                     table.insert(movements, {
--                         action = action,
--                         argument = argument,
--                     })
--                 else
--                     -- No argument, e.g. "HoldBackflip"
--                     table.insert(movements, {
--                         action = movement,
--                         argument = nil,
--                     })
--                 end
--             end
--         end
--     end

--     return movements
-- end
function parse_movements(filename)
    local movements = {}

    for line in io.lines(filename) do
        if line:match("^%s+") and line:find("%(X, Z, Angle, Cam%)") then
            local movement = line:match("^%s*(.-)%s+%(")

            -- Guano shield scoot, e.g. "GuanoShieldScootLeft [CHAIN LENGTH: 0]"
            local action, chain_length = movement:match("^(.-)%s*%[CHAIN LENGTH: (%d+)%]")

            if action then
                table.insert(movements, {
                    action = action,
                    argument = tonumber(chain_length),
                })
            else
                -- Numeric argument, e.g. "-8 ESS Turns" or "5 ESS Turns"
                local number, action = movement:match("^([%-]?%d+)%s+(.+)$")

                if number then
                    table.insert(movements, {
                        action = action,
                        argument = tonumber(number),
                    })
                else
                    -- Cardinal Turn argument, e.g. "Cardinal Turn RIGHT"
                    local action, argument = movement:match("^(.-)%s+(%S+)$")

                    if argument == "LEFT" or argument == "RIGHT" or argument == "DOWN" then
                        table.insert(movements, {
                            action = action,
                            argument = argument,
                        })
                    else
                        -- No argument, e.g. "HoldBackflip"
                        table.insert(movements, {
                            action = movement,
                            argument = nil,
                        })
                    end
                end
            end
        end
    end

    return movements
end

solution_filename = "cmg-solution.txt"
movements = parse_movements(solution_filename)
do_entire_setup = true -- true

if do_entire_setup then
    itools.load_state(8)
    v_advance(6, {}, addresses)
    --itools.load_state(9)
    for _, movement in ipairs(movements) do

        if movement.action == "ESS Turns" then
            ess_turn(movement.argument > 0, math.abs(movement.argument), addresses)
        
        elseif movement.action == "Deku Spins In Place" then
            deku_spin_in_place(movement.argument, addresses)

        elseif movement.action == "HoldSidehopLeft" then
            hold_sidehop(true, addresses)

        elseif movement.action == "HoldSidehopRight" then
            hold_sidehop(false, addresses)

        elseif movement.action == "HoldBackflip" then
            hold_backflip(addresses)

        -- elseif movement.action == "HoldDekuSpinTargeted" then
        --     hold_deku_spin(true, addresses)

        -- elseif movement.action == "HoldDekuSpinUntargeted" then
        --     hold_deku_spin(false, addresses)
        elseif movement.action == "HoldDekuSpinRight" then
            hold_deku_spin("right", false, addresses)
        elseif movement.action == "HoldDekuSpinRightTurnFirst" then
            hold_deku_spin("right", true, addresses)
        elseif movement.action == "HoldDekuSpinLeft" then
            hold_deku_spin("left", false, addresses)
        elseif movement.action == "HoldDekuSpinLeftTurnFirst" then
            hold_deku_spin("left", true, addresses)
        elseif movement.action == "HoldDekuSpinDownTurnFirst" then
            hold_deku_spin("down", true, addresses)
        elseif movement.action == "HoldDekuSpinUp" then
            hold_deku_spin("up", false, addresses)
        elseif movement.action == "Cardinal Turn" then
            if movement.argument == "LEFT" then
                cardinal_turn("LEFT", addresses)
            elseif movement.argument == "RIGHT" then
                cardinal_turn("RIGHT", addresses)
            elseif movement.argument == "DOWN" then
                cardinal_turn("DOWN", addresses)
            end

        elseif movement.action == "ShieldScootForward" then
            shield_scoot_forward(addresses)

        -- elseif movement.action == "ResetGuanoChain" then
        --     reset

        elseif movement.action == "GuanoShieldScootLeft" then
            if movement.argument > 0 then
                reset_chain = false
            elseif movement.argument == 0 then
                reset_chain = true
            end
            guano_shield_scoot(true, reset_chain, addresses)

        elseif movement.action == "GuanoShieldScootRight" then
            if movement.argument > 0 then
                reset_chain = false
            elseif movement.argument == 0 then
                reset_chain = true
            end
            guano_shield_scoot(false, reset_chain, addresses)

        end

    end
end

print("Final Position:")
print("  X Position: " .. read_memory(get_address("X Position")))
print("  Z Position: " .. read_memory(get_address("Z Position")))
print("  Angle: 0x" .. string.format("%04X", read_memory(get_address("Angle"))))
print("  Camera Angle: 0x" .. string.format("%04X", read_memory(get_address("Camera Angle"))))


extra_walking_frames = 69 --34 --59
-- cardinal_turn("DOWN", addresses)
-- itools.clear_inputs()
-- v_advance(
--         25,
--         {["A"] = true},
--         addresses
--     )

-- itools.clear_inputs()
-- v_advance(
--         6,
--         {["Z"] = true},
--         addresses
--     )
-- itools.clear_inputs()
-- v_advance(
--         4+extra_walking_frames,
--         {["Z"] = true, ["Y Axis"]=127},
--         addresses
--     )
-- itools.clear_inputs()
-- v_advance(
--         10,
--         {["Y Axis"]=127, ["A"]=true},
--         addresses
--     )


-- movements = {
--     -- "hold_sidehop_left",
--     -- "hold_sidehop_right",
--     "guanowalk_left",
--     "hold_backflip",
--     "hold_deku_spin_targeted",
--     "hold_deku_spin_untargeted",
--     "guanowalk_right",
-- }

-- for _, movement in ipairs(movements) do
--     local filename = movement .. ".csv"
--     initialize_csv(filename, addresses)

--     for initial_angle = 0x0000, 0xFFF0, 0x10 do

--         print(string.format("initial_angle = 0x%04X (%s)", initial_angle, movement))

--         itools.load_state(10)
--         memory.write_s16_be(mem["Angle"], initial_angle, 'RDRAM')
--         if movement == "hold_sidehop_left" then
--             values = hold_sidehop(true, addresses)
--         elseif movement == "hold_sidehop_right" then
--             values = hold_sidehop(false, addresses)
--         elseif movement == "hold_backflip" then
--             values = hold_backflip(addresses)
--         elseif movement == "hold_deku_spin_targeted" then
--             values = hold_deku_spin(true, addresses)
--         elseif movement == "hold_deku_spin_untargeted" then
--             values = hold_deku_spin(false, addresses)
--         elseif movement == "guanowalk_left" then
--             values = guanowalk(true, addresses)
--         elseif movement == "guanowalk_right" then
--             values = guanowalk(false, addresses)
--         end
--         append_values_to_csv(
--             filename,
--             values,
--             addresses,
--             initial_angle
--         )

--     end


-- end

-- for initial_angle = 0x8000, 0x8030, 0x10 do

--     print(string.format("initial_angle = 0x%04X", initial_angle))

--     itools.load_state(10)
--     memory.write_s16_be(mem["Angle"], initial_angle, 'RDRAM')
--     local left_values = hold_sidehop(true, addresses)
--     append_values_to_csv(
--         left_sidehop_filename,
--         left_values,
--         addresses,
--         initial_angle
--     )

--     itools.load_state(10)
--     memory.write_s16_be(mem["Angle"], initial_angle, 'RDRAM')
--     local right_values = hold_sidehop(false, addresses)
--     append_values_to_csv(
--         right_sidehop_filename,
--         right_values,
--         addresses,
--         initial_angle
--     )
-- end
