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

function hold_deku_spin(target, addresses)
    --- `target` is a boolean, True if we hold target while holding up and pressing A, False other
    local control_stick
    control_stick = 127

    local values = {}
    -- hold target for at least 6 frames before doing anything else
    append_values(values, v_advance(
        6,
        {["Z"] = true},
        addresses
    ))
    append_values(values, v_advance(
        1,
        {["Z"] = target, ["A"] = true, ["Y Axis"] = control_stick},
        addresses
    ))
    append_values(values, v_advance(
        20,
        {["Z"] = target, ["R"] = true, ["Y Axis"] = control_stick},
        addresses
    ))

    return values
end

function guanowalk(left, addresses)
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
    append_values(values, v_advance(
        32,
        {["Z"] = true, ["X Axis"] = control_stick},
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



movements = {
    -- "hold_sidehop_left",
    -- "hold_sidehop_right",
    "guanowalk_left",
    -- "hold_backflip",
    -- "hold_deku_spin_targeted",
    -- "hold_deku_spin_untargeted",
    "guanowalk_right",
}

for _, movement in ipairs(movements) do
    local filename = movement .. ".csv"
    initialize_csv(filename, addresses)

    --for initial_angle = 0x0000, 0xFFF0, 0x10 do
    for initial_angle = 0x0000, 0xFFFF, 0x1 do -- for guanowalks, you need every single angle!!!!!! for the other you just want every 0x10 bucket

        print(string.format("initial_angle = 0x%04X (%s)", initial_angle, movement))

        itools.load_state(10)
        memory.write_s16_be(mem["Angle"], initial_angle, 'RDRAM')
        if movement == "hold_sidehop_left" then
            values = hold_sidehop(true, addresses)
        elseif movement == "hold_sidehop_right" then
            values = hold_sidehop(false, addresses)
        elseif movement == "hold_backflip" then
            values = hold_backflip(addresses)
        elseif movement == "hold_deku_spin_targeted" then
            values = hold_deku_spin(true, addresses)
        elseif movement == "hold_deku_spin_untargeted" then
            values = hold_deku_spin(false, addresses)
        elseif movement == "guanowalk_left" then
            values = guanowalk(true, addresses)
        elseif movement == "guanowalk_right" then
            values = guanowalk(false, addresses)
        end
        append_values_to_csv(
            filename,
            values,
            addresses,
            initial_angle
        )

    end


end

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
