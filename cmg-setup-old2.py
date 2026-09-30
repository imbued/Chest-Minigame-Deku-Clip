"""
In order to get accurate trig computations that reflect those in the game, we need to use the lookup table below
because the game just does an approximation because it was efficient. Here are the relevant files from decomp
which I modified below for python:
https://github.com/zeldaret/mm/blob/main/src/libultra/gu/sins.c
https://github.com/zeldaret/mm/blob/main/src/libultra/gu/coss.c
https://github.com/zeldaret/mm/blob/56fa21dd0031a17cfc9e355f609542617598a265/src/code/z_lib.c#L37
"""

SINTABLE = (
    0x0000, 0x0032, 0x0064, 0x0096, 0x00C9, 0x00FB, 0x012D, 0x0160, 0x0192, 0x01C4, 0x01F7, 0x0229, 0x025B, 0x028E,
    0x02C0, 0x02F2, 0x0324, 0x0357, 0x0389, 0x03BB, 0x03EE, 0x0420, 0x0452, 0x0484, 0x04B7, 0x04E9, 0x051B, 0x054E,
    0x0580, 0x05B2, 0x05E4, 0x0617, 0x0649, 0x067B, 0x06AD, 0x06E0, 0x0712, 0x0744, 0x0776, 0x07A9, 0x07DB, 0x080D,
    0x083F, 0x0871, 0x08A4, 0x08D6, 0x0908, 0x093A, 0x096C, 0x099F, 0x09D1, 0x0A03, 0x0A35, 0x0A67, 0x0A99, 0x0ACB,
    0x0AFE, 0x0B30, 0x0B62, 0x0B94, 0x0BC6, 0x0BF8, 0x0C2A, 0x0C5C, 0x0C8E, 0x0CC0, 0x0CF2, 0x0D25, 0x0D57, 0x0D89,
    0x0DBB, 0x0DED, 0x0E1F, 0x0E51, 0x0E83, 0x0EB5, 0x0EE7, 0x0F19, 0x0F4B, 0x0F7C, 0x0FAE, 0x0FE0, 0x1012, 0x1044,
    0x1076, 0x10A8, 0x10DA, 0x110C, 0x113E, 0x116F, 0x11A1, 0x11D3, 0x1205, 0x1237, 0x1269, 0x129A, 0x12CC, 0x12FE,
    0x1330, 0x1361, 0x1393, 0x13C5, 0x13F6, 0x1428, 0x145A, 0x148C, 0x14BD, 0x14EF, 0x1520, 0x1552, 0x1584, 0x15B5,
    0x15E7, 0x1618, 0x164A, 0x167B, 0x16AD, 0x16DF, 0x1710, 0x1741, 0x1773, 0x17A4, 0x17D6, 0x1807, 0x1839, 0x186A,
    0x189B, 0x18CD, 0x18FE, 0x1930, 0x1961, 0x1992, 0x19C3, 0x19F5, 0x1A26, 0x1A57, 0x1A88, 0x1ABA, 0x1AEB, 0x1B1C,
    0x1B4D, 0x1B7E, 0x1BAF, 0x1BE1, 0x1C12, 0x1C43, 0x1C74, 0x1CA5, 0x1CD6, 0x1D07, 0x1D38, 0x1D69, 0x1D9A, 0x1DCB,
    0x1DFC, 0x1E2D, 0x1E5D, 0x1E8E, 0x1EBF, 0x1EF0, 0x1F21, 0x1F52, 0x1F82, 0x1FB3, 0x1FE4, 0x2015, 0x2045, 0x2076,
    0x20A7, 0x20D7, 0x2108, 0x2139, 0x2169, 0x219A, 0x21CA, 0x21FB, 0x222B, 0x225C, 0x228C, 0x22BD, 0x22ED, 0x231D,
    0x234E, 0x237E, 0x23AE, 0x23DF, 0x240F, 0x243F, 0x2470, 0x24A0, 0x24D0, 0x2500, 0x2530, 0x2560, 0x2591, 0x25C1,
    0x25F1, 0x2621, 0x2651, 0x2681, 0x26B1, 0x26E1, 0x2711, 0x2740, 0x2770, 0x27A0, 0x27D0, 0x2800, 0x2830, 0x285F,
    0x288F, 0x28BF, 0x28EE, 0x291E, 0x294E, 0x297D, 0x29AD, 0x29DD, 0x2A0C, 0x2A3C, 0x2A6B, 0x2A9B, 0x2ACA, 0x2AF9,
    0x2B29, 0x2B58, 0x2B87, 0x2BB7, 0x2BE6, 0x2C15, 0x2C44, 0x2C74, 0x2CA3, 0x2CD2, 0x2D01, 0x2D30, 0x2D5F, 0x2D8E,
    0x2DBD, 0x2DEC, 0x2E1B, 0x2E4A, 0x2E79, 0x2EA8, 0x2ED7, 0x2F06, 0x2F34, 0x2F63, 0x2F92, 0x2FC0, 0x2FEF, 0x301E,
    0x304C, 0x307B, 0x30A9, 0x30D8, 0x3107, 0x3135, 0x3163, 0x3192, 0x31C0, 0x31EF, 0x321D, 0x324B, 0x3279, 0x32A8,
    0x32D6, 0x3304, 0x3332, 0x3360, 0x338E, 0x33BC, 0x33EA, 0x3418, 0x3446, 0x3474, 0x34A2, 0x34D0, 0x34FE, 0x352B,
    0x3559, 0x3587, 0x35B5, 0x35E2, 0x3610, 0x363D, 0x366B, 0x3698, 0x36C6, 0x36F3, 0x3721, 0x374E, 0x377C, 0x37A9,
    0x37D6, 0x3803, 0x3831, 0x385E, 0x388B, 0x38B8, 0x38E5, 0x3912, 0x393F, 0x396C, 0x3999, 0x39C6, 0x39F3, 0x3A20,
    0x3A4D, 0x3A79, 0x3AA6, 0x3AD3, 0x3B00, 0x3B2C, 0x3B59, 0x3B85, 0x3BB2, 0x3BDE, 0x3C0B, 0x3C37, 0x3C64, 0x3C90,
    0x3CBC, 0x3CE9, 0x3D15, 0x3D41, 0x3D6D, 0x3D99, 0x3DC5, 0x3DF1, 0x3E1D, 0x3E49, 0x3E75, 0x3EA1, 0x3ECD, 0x3EF9,
    0x3F25, 0x3F50, 0x3F7C, 0x3FA8, 0x3FD3, 0x3FFF, 0x402B, 0x4056, 0x4082, 0x40AD, 0x40D8, 0x4104, 0x412F, 0x415A,
    0x4186, 0x41B1, 0x41DC, 0x4207, 0x4232, 0x425D, 0x4288, 0x42B3, 0x42DE, 0x4309, 0x4334, 0x435F, 0x4389, 0x43B4,
    0x43DF, 0x4409, 0x4434, 0x445F, 0x4489, 0x44B4, 0x44DE, 0x4508, 0x4533, 0x455D, 0x4587, 0x45B1, 0x45DC, 0x4606,
    0x4630, 0x465A, 0x4684, 0x46AE, 0x46D8, 0x4702, 0x472C, 0x4755, 0x477F, 0x47A9, 0x47D2, 0x47FC, 0x4826, 0x484F,
    0x4879, 0x48A2, 0x48CC, 0x48F5, 0x491E, 0x4948, 0x4971, 0x499A, 0x49C3, 0x49EC, 0x4A15, 0x4A3E, 0x4A67, 0x4A90,
    0x4AB9, 0x4AE2, 0x4B0B, 0x4B33, 0x4B5C, 0x4B85, 0x4BAD, 0x4BD6, 0x4BFE, 0x4C27, 0x4C4F, 0x4C78, 0x4CA0, 0x4CC8,
    0x4CF0, 0x4D19, 0x4D41, 0x4D69, 0x4D91, 0x4DB9, 0x4DE1, 0x4E09, 0x4E31, 0x4E58, 0x4E80, 0x4EA8, 0x4ED0, 0x4EF7,
    0x4F1F, 0x4F46, 0x4F6E, 0x4F95, 0x4FBD, 0x4FE4, 0x500B, 0x5032, 0x505A, 0x5081, 0x50A8, 0x50CF, 0x50F6, 0x511D,
    0x5144, 0x516B, 0x5191, 0x51B8, 0x51DF, 0x5205, 0x522C, 0x5253, 0x5279, 0x52A0, 0x52C6, 0x52EC, 0x5313, 0x5339,
    0x535F, 0x5385, 0x53AB, 0x53D1, 0x53F7, 0x541D, 0x5443, 0x5469, 0x548F, 0x54B5, 0x54DA, 0x5500, 0x5525, 0x554B,
    0x5571, 0x5596, 0x55BB, 0x55E1, 0x5606, 0x562B, 0x5650, 0x5675, 0x569B, 0x56C0, 0x56E5, 0x5709, 0x572E, 0x5753,
    0x5778, 0x579D, 0x57C1, 0x57E6, 0x580A, 0x582F, 0x5853, 0x5878, 0x589C, 0x58C0, 0x58E5, 0x5909, 0x592D, 0x5951,
    0x5975, 0x5999, 0x59BD, 0x59E1, 0x5A04, 0x5A28, 0x5A4C, 0x5A6F, 0x5A93, 0x5AB7, 0x5ADA, 0x5AFD, 0x5B21, 0x5B44,
    0x5B67, 0x5B8B, 0x5BAE, 0x5BD1, 0x5BF4, 0x5C17, 0x5C3A, 0x5C5D, 0x5C7F, 0x5CA2, 0x5CC5, 0x5CE7, 0x5D0A, 0x5D2D,
    0x5D4F, 0x5D71, 0x5D94, 0x5DB6, 0x5DD8, 0x5DFA, 0x5E1D, 0x5E3F, 0x5E61, 0x5E83, 0x5EA5, 0x5EC6, 0x5EE8, 0x5F0A,
    0x5F2C, 0x5F4D, 0x5F6F, 0x5F90, 0x5FB2, 0x5FD3, 0x5FF4, 0x6016, 0x6037, 0x6058, 0x6079, 0x609A, 0x60BB, 0x60DC,
    0x60FD, 0x611E, 0x613E, 0x615F, 0x6180, 0x61A0, 0x61C1, 0x61E1, 0x6202, 0x6222, 0x6242, 0x6263, 0x6283, 0x62A3,
    0x62C3, 0x62E3, 0x6303, 0x6323, 0x6342, 0x6362, 0x6382, 0x63A1, 0x63C1, 0x63E0, 0x6400, 0x641F, 0x643F, 0x645E,
    0x647D, 0x649C, 0x64BB, 0x64DA, 0x64F9, 0x6518, 0x6537, 0x6556, 0x6574, 0x6593, 0x65B2, 0x65D0, 0x65EF, 0x660D,
    0x662B, 0x664A, 0x6668, 0x6686, 0x66A4, 0x66C2, 0x66E0, 0x66FE, 0x671C, 0x673A, 0x6757, 0x6775, 0x6792, 0x67B0,
    0x67CD, 0x67EB, 0x6808, 0x6825, 0x6843, 0x6860, 0x687D, 0x689A, 0x68B7, 0x68D4, 0x68F1, 0x690D, 0x692A, 0x6947,
    0x6963, 0x6980, 0x699C, 0x69B9, 0x69D5, 0x69F1, 0x6A0E, 0x6A2A, 0x6A46, 0x6A62, 0x6A7E, 0x6A9A, 0x6AB5, 0x6AD1,
    0x6AED, 0x6B08, 0x6B24, 0x6B40, 0x6B5B, 0x6B76, 0x6B92, 0x6BAD, 0x6BC8, 0x6BE3, 0x6BFE, 0x6C19, 0x6C34, 0x6C4F,
    0x6C6A, 0x6C84, 0x6C9F, 0x6CBA, 0x6CD4, 0x6CEF, 0x6D09, 0x6D23, 0x6D3E, 0x6D58, 0x6D72, 0x6D8C, 0x6DA6, 0x6DC0,
    0x6DDA, 0x6DF3, 0x6E0D, 0x6E27, 0x6E40, 0x6E5A, 0x6E73, 0x6E8D, 0x6EA6, 0x6EBF, 0x6ED9, 0x6EF2, 0x6F0B, 0x6F24,
    0x6F3D, 0x6F55, 0x6F6E, 0x6F87, 0x6FA0, 0x6FB8, 0x6FD1, 0x6FE9, 0x7002, 0x701A, 0x7032, 0x704A, 0x7062, 0x707A,
    0x7092, 0x70AA, 0x70C2, 0x70DA, 0x70F2, 0x7109, 0x7121, 0x7138, 0x7150, 0x7167, 0x717E, 0x7196, 0x71AD, 0x71C4,
    0x71DB, 0x71F2, 0x7209, 0x7220, 0x7236, 0x724D, 0x7264, 0x727A, 0x7291, 0x72A7, 0x72BD, 0x72D4, 0x72EA, 0x7300,
    0x7316, 0x732C, 0x7342, 0x7358, 0x736E, 0x7383, 0x7399, 0x73AE, 0x73C4, 0x73D9, 0x73EF, 0x7404, 0x7419, 0x742E,
    0x7443, 0x7458, 0x746D, 0x7482, 0x7497, 0x74AC, 0x74C0, 0x74D5, 0x74EA, 0x74FE, 0x7512, 0x7527, 0x753B, 0x754F,
    0x7563, 0x7577, 0x758B, 0x759F, 0x75B3, 0x75C7, 0x75DA, 0x75EE, 0x7601, 0x7615, 0x7628, 0x763B, 0x764F, 0x7662,
    0x7675, 0x7688, 0x769B, 0x76AE, 0x76C1, 0x76D3, 0x76E6, 0x76F9, 0x770B, 0x771E, 0x7730, 0x7742, 0x7754, 0x7767,
    0x7779, 0x778B, 0x779D, 0x77AF, 0x77C0, 0x77D2, 0x77E4, 0x77F5, 0x7807, 0x7818, 0x782A, 0x783B, 0x784C, 0x785D,
    0x786E, 0x787F, 0x7890, 0x78A1, 0x78B2, 0x78C3, 0x78D3, 0x78E4, 0x78F4, 0x7905, 0x7915, 0x7925, 0x7936, 0x7946,
    0x7956, 0x7966, 0x7976, 0x7985, 0x7995, 0x79A5, 0x79B5, 0x79C4, 0x79D4, 0x79E3, 0x79F2, 0x7A02, 0x7A11, 0x7A20,
    0x7A2F, 0x7A3E, 0x7A4D, 0x7A5B, 0x7A6A, 0x7A79, 0x7A87, 0x7A96, 0x7AA4, 0x7AB3, 0x7AC1, 0x7ACF, 0x7ADD, 0x7AEB,
    0x7AF9, 0x7B07, 0x7B15, 0x7B23, 0x7B31, 0x7B3E, 0x7B4C, 0x7B59, 0x7B67, 0x7B74, 0x7B81, 0x7B8E, 0x7B9B, 0x7BA8,
    0x7BB5, 0x7BC2, 0x7BCF, 0x7BDC, 0x7BE8, 0x7BF5, 0x7C02, 0x7C0E, 0x7C1A, 0x7C27, 0x7C33, 0x7C3F, 0x7C4B, 0x7C57,
    0x7C63, 0x7C6F, 0x7C7A, 0x7C86, 0x7C92, 0x7C9D, 0x7CA9, 0x7CB4, 0x7CBF, 0x7CCB, 0x7CD6, 0x7CE1, 0x7CEC, 0x7CF7,
    0x7D02, 0x7D0C, 0x7D17, 0x7D22, 0x7D2C, 0x7D37, 0x7D41, 0x7D4B, 0x7D56, 0x7D60, 0x7D6A, 0x7D74, 0x7D7E, 0x7D88,
    0x7D91, 0x7D9B, 0x7DA5, 0x7DAE, 0x7DB8, 0x7DC1, 0x7DCB, 0x7DD4, 0x7DDD, 0x7DE6, 0x7DEF, 0x7DF8, 0x7E01, 0x7E0A,
    0x7E13, 0x7E1B, 0x7E24, 0x7E2C, 0x7E35, 0x7E3D, 0x7E45, 0x7E4D, 0x7E56, 0x7E5E, 0x7E66, 0x7E6D, 0x7E75, 0x7E7D,
    0x7E85, 0x7E8C, 0x7E94, 0x7E9B, 0x7EA3, 0x7EAA, 0x7EB1, 0x7EB8, 0x7EBF, 0x7EC6, 0x7ECD, 0x7ED4, 0x7EDB, 0x7EE1,
    0x7EE8, 0x7EEE, 0x7EF5, 0x7EFB, 0x7F01, 0x7F08, 0x7F0E, 0x7F14, 0x7F1A, 0x7F20, 0x7F25, 0x7F2B, 0x7F31, 0x7F36,
    0x7F3C, 0x7F41, 0x7F47, 0x7F4C, 0x7F51, 0x7F56, 0x7F5B, 0x7F60, 0x7F65, 0x7F6A, 0x7F6F, 0x7F74, 0x7F78, 0x7F7D,
    0x7F81, 0x7F85, 0x7F8A, 0x7F8E, 0x7F92, 0x7F96, 0x7F9A, 0x7F9E, 0x7FA2, 0x7FA6, 0x7FA9, 0x7FAD, 0x7FB0, 0x7FB4,
    0x7FB7, 0x7FBA, 0x7FBE, 0x7FC1, 0x7FC4, 0x7FC7, 0x7FCA, 0x7FCC, 0x7FCF, 0x7FD2, 0x7FD4, 0x7FD7, 0x7FD9, 0x7FDC,
    0x7FDE, 0x7FE0, 0x7FE2, 0x7FE4, 0x7FE6, 0x7FE8, 0x7FEA, 0x7FEC, 0x7FED, 0x7FEF, 0x7FF1, 0x7FF2, 0x7FF3, 0x7FF5,
    0x7FF6, 0x7FF7, 0x7FF8, 0x7FF9, 0x7FFA, 0x7FFB, 0x7FFB, 0x7FFC, 0x7FFD, 0x7FFD, 0x7FFE, 0x7FFE, 0x7FFE, 0x7FFE,
    0x7FFE, 0x7FFF,
)

def sins(x: int) -> int:
    x >>= 4

    if x & 0x400:
        val = SINTABLE[0x3FF - (x & 0x3FF)]
    else:
        val = SINTABLE[x & 0x3FF]

    if x & 0x800:
        return -val

    return val

def coss(x: int) -> int:
    return sins(x + 0x4000)

def Math_SinS(x: int) -> float:
    return sins(x) / 32767.0

def Math_CosS(x: int) -> float:
    return coss(x) / 32767.0

"""
In order to compute the x and z velocities, we need to know:
    1) The linear velocity during every frame of the movement
    2) The movement angle during every frame of the movement
Then we can do:
    x_velocity = linear_velocity * Math_SinS(movement_angle)
    z_velocity = linear_velocity * Math_CosS(movement_angle)

I will record the linear velocities and movement angles for movements at camera angle 0x0000 and then I can get the camera angle associated
with whatever facing angle we have (using a lookup table that maps "facing angle" to "camera angle while holding target on flat ground while 
not too close to walls") and then I can add on whatever the movement angle at 0x0000 was to the current camera angle to get the current
movement angle.
"""

VELOCITY_SCALE = 1.5 # if moving with a velocity of 1 for 1 frame, you move 1.5 position units
TOTAL_ANGLES = 0x10000

def hold_sidehop(x_pos, z_pos, angle, camera_angle, left=True):
    """
    Just a basic hold sidehop for now. Might do a move general sidehop function in the future where you can hold into guano walk or release early
    would need to account for ending guano early with holding target or without and shield or no shield and if doing this then might as well allow
    releasing control stick and/or early during sidehop, etc.

    Inefficient implementation of computing velocities might look like:
    ```
     sidehop_linear_velocities = [8.5, 8.4, 8.299999, 8.199999, 8.099998, 7.999999, 6.999999]
        movement_angle_offset = 0x4000 if left else -0x4000
        movement_angle = (camera_angle + movement_angle_offset) % 0x10000
        sidehop_movement_angles = [movement_angle for _ in sidehop_linear_velocities] 
    
        # instead of computing the x and z velocities at every frame, we just need the final 
        cumulative_x_velocity = 0
        cumulative_z_velocity = 0
        for v, a in zip(sidehop_linear_velocities, sidehop_movement_angles):
            cumulative_x_velocity += v * Math_SinS(a)
            cumulative_z_velocity += v * Math_CosS(a)
        return (cumulative_x_velocity, cumulative_z_velocity)
    ```
    but I precompute sums to make it a little faster
    """
    movement_angle_offset = 0x4000 if left else -0x4000
    movement_angle = (camera_angle + movement_angle_offset) % TOTAL_ANGLES
    cumulative_linear_velocity = 56.499994 # sum([8.5, 8.4, 8.299999, 8.199999, 8.099998, 7.999999, 6.999999])
    cumulative_x_velocity = cumulative_linear_velocity * Math_SinS(movement_angle)
    cumulative_z_velocity = cumulative_linear_velocity * Math_CosS(movement_angle)

    updated_x_pos = x_pos + VELOCITY_SCALE * cumulative_x_velocity 
    updated_z_pos = z_pos + VELOCITY_SCALE * cumulative_z_velocity
    return updated_x_pos, updated_z_pos, angle

def guano_shield_scoot(x_pos, z_pos, angle, camera_angle, guano_chain_length=0, left=True):
    """
    linear velocity is 2 for 2 frames

    down-left is the same as cardinal turn down + guano shield scoot right
    down-right is the same as cardinal turn down + guano shield scoot left

    Because of symmetry, I am ignoring those cases to reduce the number of permutations
    """
    cumulative_linear_velocity = 4 # sum([2, 2])

    movement_angle_offset_list = [0x0999, 0x0828, 0x06EE, 0x05E5, 0x0502, 0x0442, 0x039F, 0x0313, 0x029E, 0x023A, 0x01E4]
    if guano_chain_length >= len(movement_angle_offset_list):
        raise NotImplementedError(f"I have only implemented the first {len(movement_angle_offset_list)} movement values, got {guano_chain_length=}")
    movement_angle_offset = movement_angle_offset_list[guano_chain_length]
    if not left:
        movement_angle_offset = -movement_angle_offset

    movement_angle = (camera_angle + movement_angle_offset) % TOTAL_ANGLES
    cumulative_x_velocity = cumulative_linear_velocity * Math_SinS(movement_angle)
    cumulative_z_velocity = cumulative_linear_velocity * Math_CosS(movement_angle)

    updated_x_pos = x_pos + VELOCITY_SCALE * cumulative_x_velocity 
    updated_z_pos = z_pos + VELOCITY_SCALE * cumulative_z_velocity
    return updated_x_pos, updated_z_pos, angle

def shield_scoot_forward(x_pos, z_pos, angle, camera_angle):
    cumulative_linear_velocity = 4 # sum([2, 2])
    movement_angle = camera_angle
    cumulative_x_velocity = cumulative_linear_velocity * Math_SinS(movement_angle)
    cumulative_z_velocity = cumulative_linear_velocity * Math_CosS(movement_angle)

    updated_x_pos = x_pos + VELOCITY_SCALE * cumulative_x_velocity 
    updated_z_pos = z_pos + VELOCITY_SCALE * cumulative_z_velocity
    return updated_x_pos, updated_z_pos, angle

def hold_backflip(x_pos, z_pos, angle, camera_angle):
    """
    backflip_linear_velocities = [6, 5.9, 5.8, 5.7, 5.6, 5.5, 5.400001, 5.300001, 5.200001, 5.100001, 5.000001, 4.000001]
    """
    movement_angle_offset = 0x8000
    movement_angle = (camera_angle + movement_angle_offset) % TOTAL_ANGLES
    cumulative_linear_velocity = 64.500006 # sum([6, 5.9, 5.8, 5.7, 5.6, 5.5, 5.400001, 5.300001, 5.200001, 5.100001, 5.000001, 4.000001])
    cumulative_x_velocity = cumulative_linear_velocity * Math_SinS(movement_angle)
    cumulative_z_velocity = cumulative_linear_velocity * Math_CosS(movement_angle)

    updated_x_pos = x_pos + VELOCITY_SCALE * cumulative_x_velocity 
    updated_z_pos = z_pos + VELOCITY_SCALE * cumulative_z_velocity
    return updated_x_pos, updated_z_pos, angle

def hold_deku_spin(x_pos, z_pos, angle, camera_angle):
    """
    Importantly, this assumes you hold shield at the end of the spin

    deku_spin_linear_velocities = [2, 4, 6, 8, 8.772973, 8.383783, 7.994595, 7.605406, 7.216217, 6.827027, 6.437838, 6.048649, 5.65946, 5.27027, 4.881081, 4.881081] # repeated value at end might be due to holding shield as shield often repeats your last velocity for 1 frame
    """
    movement_angle_offset = 0x0000
    movement_angle = (camera_angle + movement_angle_offset) % TOTAL_ANGLES
    cumulative_linear_velocity = 99.97837999999999 # [2, 4, 6, 8, 8.772973, 8.383783, 7.994595, 7.605406, 7.216217, 6.827027, 6.437838, 6.048649, 5.65946, 5.27027, 4.881081, 4.881081]
    cumulative_x_velocity = cumulative_linear_velocity * Math_SinS(movement_angle)
    cumulative_z_velocity = cumulative_linear_velocity * Math_CosS(movement_angle)

    updated_x_pos = x_pos + VELOCITY_SCALE * cumulative_x_velocity 
    updated_z_pos = z_pos + VELOCITY_SCALE * cumulative_z_velocity
    return updated_x_pos, updated_z_pos, angle

def ess_turn(x_pos, z_pos, angle, camera_angle, num_turns):
    """
    `num_turns` > 0 means ESS turns left, `num_turns` < 0 means ESS turns right
    """
    if num_turns == 0:
        raise ValueError(f"Got {num_turns=}, but it should be positive or negative")
    angle_offset = 0x708

    new_angle = (angle + num_turns * angle_offset) % TOTAL_ANGLES
    return x_pos, z_pos, new_angle

def deku_spin_in_place(x_pos, z_pos, angle, camera_angle, num_spins):
    angle_offset = -0x1E0
    new_angle = (angle + num_spins * angle_offset) % TOTAL_ANGLES
    return x_pos, z_pos, new_angle

def cardinal_turn(x_pos, z_pos, angle, camera_angle, direction):
    if direction == "UP":
        angle_offset = 0x0000
    elif direction == "LEFT":
        angle_offset = 0x4000
    elif direction == "DOWN":
        angle_offset = 0x8000
    elif direction == "RIGHT":
        angle_offset = 0xC000
    else:
        raise ValueError(f"invalid direction, got {direction=}")

    new_angle = (camera_angle + angle_offset) % TOTAL_ANGLES
    return x_pos, z_pos, new_angle

"""
To get the targeted camera angle corresponding to a given facing angle (on flat ground and not too close to a wall), I use a lookup table
that I obtain by running a lua script
"""

FacingAngleToTargetedCameraAngle = {
    # TODO
}

def position_is_valid(x_pos, z_pos):

    # this bans some parts of the checkerboard area, but I don't have to worry about checking for moving diagonal through the wall
    if z_pos > 826 or z_pos < 134:
        return False

    if x_pos > 66 or x_pos < -1666:
        return False

    # slanted part of counter near clip location
    if z_pos >= 797 and x_pos <= -174 and x_pos >= -243.7903 and x_pos >= ((-243.7903 - -180.3072)/(826 - 797.6762))* (z_pos - 826) + -243.7903:
        return False

    # slanted part of counter to the left side of the room
    if 15 <= x_pos <= 66 and x_pos <= ((66 - 15)/(818.1763 - 797))*(z_pos - 797) + 15:
        return False

    # # checkboard area, these will never execute in practice so commenting it for now
    # if z_pos > 826 and x_pos > -375:
    #     return False
    # if z_pos < 134 and x_pos > -374:
    #     return False
    # if z_pos < 14:
    #     return False
    # if z_pos > 946:
    #     return False
    return True

def position_is_solution(x_pos, z_pos):
    pass # TODO, need number of frames to walk before spinning!!


def position_str(x, z, angle):
    camera_angle = FacingAngleToTargetedCameraAngle[angle]
    return f"    (X, Z, Angle, Cam)=({x}, {z}, {hex(angle)}, {hex(camera_angle)})"

def log_solution(x0, z0, a0, sol_x, sol_z, sol_a, action_log, filename):
    with open(filename, 'a') as f:
        f.write(f"-"*30)
        f.write(f"Solution Position: {position_str(sol_x, sol_z, sol_a)}\n")
        f.write(f"Initial Position: {position_str(x0, z0, a0)}\n")
        for action in action_log:
            f.write(f"    {action}\n")
        # TODO somehow fetch which angle is needed for the solution position
        # TODO WE ALSO NEED HOW MANY FRAMES OF WALKING FORWARD IS NEEDED FOR THE DEKU SPIN CLIP (assuming you have correct angle)!!!!!!!!!!!!
        

MovementCosts = {
    "HoldSidehopLeft" : 1,
    "HoldSidehopRight" : 1,
    "GuanoShieldScootLeft" : 1,
    "GuanoShieldScootRight" : 1,
    "ShieldScootForward" : 1,
    "HoldBackflip" : 1,
    "HoldDekuSpin" : 1,
}

AngleCosts = {
    "ESSTurn": 1,
    "CardinalTurn": 0.5,
    "DekuSpinInPlace" : 1,
    "ResetGuanoChain" : 0,
    "NULL": 0,
}


MAX_COST = 10
MAX_ESS_TURNS = 8 # e.g. -8, -7, ..., -1, 1, ..., 7, 8 (i.e. do negative and positive but skip 0)
ESS_OPTIONS = [a for a in range(-MAX_ESS_TURNS, MAX_ESS_TURNS+1) if a != 0]
MAX_DEKU_SPINS_IN_PLACE = 3
MAX_GUANO_CHAIN_LENGTH = 5

def find_solutions(x0, z0, a0, filename):
    """
    `x0` initial x position
    `z0` initial z position
    `a0` initial angle
    `filename` of txt file we save solutions to
    """


    success_count = [0]
    failure_count = [0]
    def dfs(x, z, a, angle_turn=True, guano_chain_length=0, action_log=[], cost=0):

        if cost > MAX_COST:
            failure_count[0] += 1
            return False
        if guano_chain_length > MAX_GUANO_CHAIN_LENGTH:
            failure_count[0] += 1
            return False
        if not position_is_valid(x, z):
            failure_count[0] += 1
            return False

        camera_angle = FacingAngleToTargetedCameraAngle[a]

        if position_is_solution(x, z):
            log_solution(x0=x0, z0=z0, a0=a0, sol_x=x, sol_z=z, sol_a=a, action_log=action_log, filename=filename)
            success_count[0] += 1
            print(f"{success_count[0]} Solutions Found, {failure_count[0]} Failures")
            return True # I don't think return value really matters, just terminates the dfs branch

        if angle_turn:
            for angle_option in AngleCosts:
                if angle_option != "NULL":
                    guano_chain_length = 0

                if angle_option == "ESSTurn":
                    for num_turns in ESS_OPTIONS:
                        new_x, new_z, new_a = ess_turn(x_pos=x, z_pos=z, angle=a, camera_angle=camera_angle, num_turns=num_turns)
                        action_log.append(f"{num_turns} ESS Turns" + position_str(x=new_x, z=new_z, angle=new_a))
                        dfs(x=new_x, z=new_z, a=new_a, angle_turn=not angle_turn, guano_chain_length=guano_chain_length, action_log=action_log, cost=cost+AngleCosts[angle_option])
                        action_log.pop()
                elif angle_option == "CardinalTurn":
                    for direction in ['LEFT', 'RIGHT', 'DOWN']:
                        new_x, new_z, new_a = cardinal_turn(x_pos=x, z_pos=z, angle=a, camera_angle=camera_angle, direction=direction)
                        action_log.append(f"Cardinal Turn {direction}" + position_str(x=new_x, z=new_z, angle=new_a))
                        dfs(x=new_x, z=new_z, a=new_a, angle_turn=not angle_turn, guano_chain_length=guano_chain_length, action_log=action_log, cost=cost+AngleCosts[angle_option])
                        action_log.pop()
                elif angle_option == "DekuSpinInPlace":
                    for num_deku_spins in range(1, MAX_DEKU_SPINS_IN_PLACE+1):
                        new_x, new_z, new_a = deku_spin_in_place(x_pos=x, z_pos=z, angle=a, camera_angle=camera_angle, num_spins=num_deku_spins)
                        action_log.append(f"{num_deku_spins} Deku Spins In Place" + position_str(x=new_x, z=new_z, angle=new_a))
                        dfs(x=new_x, z=new_z, a=new_a, angle_turn=not angle_turn, guano_chain_length=guano_chain_length, action_log=action_log, cost=cost+AngleCosts[angle_option]*num_deku_spins)
                        action_log.pop()
                elif angle_option == "NULL":
                    dfs(x=x, z=z, a=a, angle_turn=not angle_turn, guano_chain_length=guano_chain_length, action_log=action_log, cost=cost)
                elif angle_option == "ResetGuanoChain":
                    action_log.append(f"{angle_option}" + position_str(x=new_x, z=new_z, angle=new_a))
                    dfs(x=new_x, z=new_z, a=new_a, angle_turn=not angle_turn, guano_chain_length=0, action_log=action_log, cost=cost+AngleCosts[angle_option])
                    action_log.pop()
                else:
                    raise ValueError("typo??")
        else: # if not angle_turn, we pick a movement option instead

            for movement_option in MovementCosts:
                if movement_option in {"HoldSidehopLeft", "HoldSidehopRight"}:
                    new_x, new_z, new_a = hold_sidehop(x_pos=x, z_pos=z, angle=a, camera_angle=camera_angle, left=movement_option=="HoldSidehopLeft")
                    action_log.append(f"{movement_option}" + position_str(x=new_x, z=new_z, angle=new_a))
                    dfs(x=new_x, z=new_z, a=new_a, angle_turn=not angle_turn, guano_chain_length=0, action_log=action_log, cost=cost+MovementCosts[movement_option])
                    action_log.pop()
                elif movement_option in {"GuanoShieldScootLeft", "GuanoShieldScootRight"}:
                    new_x, new_z, new_a = guano_shield_scoot(x_pos=x, z_pos=z, angle=a, camera_angle=camera_angle, guano_chain_length=guano_chain_length, left=movement_option=="GuanoShieldScootLeft")
                    action_log.append(f"{movement_option}" + position_str(x=new_x, z=new_z, angle=new_a))
                    dfs(x=new_x, z=new_z, a=new_a, angle_turn=not angle_turn, guano_chain_length=guano_chain_length+1, action_log=action_log, cost=cost+MovementCosts[movement_option])
                    action_log.pop()
                elif movement_option == "ShieldScootForward":
                    new_x, new_z, new_a = shield_scoot_forward(x_pos=x, z_pos=z, angle=a, camera_angle=camera_angle)
                    action_log.append(f"{movement_option}" + position_str(x=new_x, z=new_z, angle=new_a))
                    dfs(x=new_x, z=new_z, a=new_a, angle_turn=not angle_turn, guano_chain_length=0, action_log=action_log, cost=cost+MovementCosts[movement_option])
                    action_log.pop()
                elif movement_option == "HoldBackflip":
                    new_x, new_z, new_a = hold_backflip(x_pos=x, z_pos=z, angle=a, camera_angle=camera_angle)
                    action_log.append(f"{movement_option}" + position_str(x=new_x, z=new_z, angle=new_a))
                    dfs(x=new_x, z=new_z, a=new_a, angle_turn=not angle_turn, guano_chain_length=0, action_log=action_log, cost=cost+MovementCosts[movement_option])
                    action_log.pop()
                elif movement_option == "HoldDekuSpin":
                    new_x, new_z, new_a = hold_deku_spin(x_pos=x, z_pos=z, angle=a, camera_angle=camera_angle)
                    action_log.append(f"{movement_option}" + position_str(x=new_x, z=new_z, angle=new_a))
                    dfs(x=new_x, z=new_z, a=new_a, angle_turn=not angle_turn, guano_chain_length=0, action_log=action_log, cost=cost+MovementCosts[movement_option])
                    action_log.pop()
                else:
                    raise ValueError("typo???")


            
    dfs(x=x0, z=z0, a=a0, angle_turn=True, guano_chain_length=0, action_log=[], cost=0)









x, z = (-239.8633, 824.175)


new_x = x - 48 * Math_SinS(0xFF90)
new_z = z - 48 * Math_CosS(0xFF90)

import code; code.interact(local=locals())


import sys; sys.exit(0)

assert False
def get_xz_vel(linear_velocity, movement_angle):
    x_velocity = linear_velocity * Math_SinS(movement_angle)
    z_velocity = linear_velocity * Math_CosS(movement_angle)
    return (x_velocity, z_velocity)

print(f"{get_xz_vel(linear_velocity=0.8999996 , movement_angle=0x1CD8)}")

x_pos, z_pos, angle, camera_angle = -70, 209.75, 0x0000, 0x0000
new_x, new_z, new_angle = hold_sidehop(x_pos=x_pos, z_pos=z_pos, angle=angle, camera_angle=camera_angle, left=False)
print(f"ORIGINAL: {(x_pos, z_pos, angle)}")
print(f"NEW     : {(new_x, new_z, new_angle)}")



angles = [
    0x8000,
    0x7667,
    0x6E3F,
    0x6751,
    0x616C,
    0x5C6A,
    0x5828,
    0x5489,
    0x5176,
    0x4ED8,
    0x4C9E,
    0x4ABA,
]

diffs = []
for i in range(len(angles)-1):
    diffs.append(hex(angles[i] - angles[i+1]))
print(f"{diffs=}")

assert False
x, z = (0.4655294, -1.945006)

movement_angle = 0x7667
facing_angle = 0xD4A6
combined_angle = (movement_angle + facing_angle) % 0x10000  # = 0x4B0D -- this is the new movement angle, you add them because 0x7667 corresponded to angle 0x0000
# so in practice i need the movement angle at 0x0000 and the x and z velocities for each movement option, then i can compute everything

speed = 2.0
new_x = speed * Math_SinS(combined_angle)
new_z = speed * Math_CosS(combined_angle)
print(new_x, new_z)


test_angle = 0x6E3F
test_x =2 * Math_SinS(test_angle)
test_z = 2 * Math_CosS(test_angle)
print(f"{test_x=}, {test_z=}")

#z, x = (2, 0)
# angle = (0x4b0d - 0x7667) % 0x10000 #(0x7667 - 0x4B0D)  #0xD4A6#0x2679 #0x0030
# def rotate(x, z, angle):
#     cos = Math_CosS(angle)
#     sin = Math_SinS(angle)
#     return ( sin * z + cos * x ,  cos * z - sin * x)

# res = rotate(x=x, z=z, angle=angle)
# print(f"{res=}")

# def l2norm(tup):
#     x, z = tup
#     return (x**2 + z**2)**0.5
# print(f"{l2norm(res)=}")
# print(f"{l2norm((x, z))=}")

import code; code.interact(local=locals())