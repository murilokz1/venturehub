local UILib = loadstring(game:HttpGet('https://raw.githubusercontent.com/StepBroFurious/Script/main/HydraHubUi.lua'))()
local Player = game.Players.LocalPlayer

local Window = UILib.new("Exploit Tester Panel", Player.UserId, "Developer")

--[[ CATEGORIAS ]]--
local Visuals = Window:Category("Visuals", "http://www.roblox.com/asset/?id=8395747586")
local Aim = Window:Category("Aim", "http://www.roblox.com/asset/?id=8395747586")
local Misc = Window:Category("Miscellaneous", "http://www.roblox.com/asset/?id=8395747586")
local Settings = Window:Category("Settings", "http://www.roblox.com/asset/?id=8395747586")

--[[ VARIÁVEIS INTERNAS ]]--
local espSettings = {
    enabled = false,
    boxes = false,
    names = false,
    lines = false,
    showDistance = false,
    teamCheck = true,
    colors = {
        box = Color3.fromRGB(255, 0, 0),
        name = Color3.fromRGB(0, 255, 0),
        line = Color3.fromRGB(0, 0, 255),
        distance = Color3.fromRGB(255, 255, 0)
    }
}

local aimbotSettings = {
    enabled = false,
    fov = 100,
    showFov = true,
    fovColor = Color3.fromRGB(255, 255, 255),
    smoothness = 0.1,
    teamCheck = true,
    key = Enum.KeyCode.E
}

local silentAimSettings = {
    enabled = false,
    fov = 80,
    smoothness = 0.1,
    showFov = true,
    teamCheck = true
}

local miscSettings = {
    walkspeed = 16,
    jumppower = 50,
    gravity = 196.2,
    fly = false,
    noclip = false
}

--[[ FUNÇÕES UTILITÁRIAS ]]--
local function applyESP()
    print("ESP atualizado:", espSettings)
end

local function applyAimbot()
    print("Aimbot atualizado:", aimbotSettings)
end

local function applySilentAim()
    print("Silent Aim atualizado:", silentAimSettings)
end

--[[ VISUALS ]]--
local vSec = Visuals:Button("ESP", "http://www.roblox.com/asset/?id=8395747586"):Section("ESP Configs", "Left")

vSec:Toggle({Title="Enable ESP", Default=false}, function(v) espSettings.enabled = v applyESP() end)
vSec:Toggle({Title="Show Boxes", Default=false}, function(v) espSettings.boxes = v applyESP() end)
vSec:ColorPicker({Title="Box Color", Default=espSettings.colors.box}, function(v) espSettings.colors.box = v end)
vSec:Toggle({Title="Show Names", Default=false}, function(v) espSettings.names = v applyESP() end)
vSec:ColorPicker({Title="Name Color", Default=espSettings.colors.name}, function(v) espSettings.colors.name = v end)
vSec:Toggle({Title="Show Lines", Default=false}, function(v) espSettings.lines = v applyESP() end)
vSec:ColorPicker({Title="Line Color", Default=espSettings.colors.line}, function(v) espSettings.colors.line = v end)
vSec:Toggle({Title="Show Distance", Default=false}, function(v) espSettings.showDistance = v applyESP() end)
vSec:ColorPicker({Title="Distance Color", Default=espSettings.colors.distance}, function(v) espSettings.colors.distance = v end)
vSec:Toggle({Title="Team Check", Default=true}, function(v) espSettings.teamCheck = v applyESP() end)

--[[ AIM ]]--
local aSec = Aim:Button("Aimbot", "http://www.roblox.com/asset/?id=8395747586"):Section("Aimbot Configs", "Left")
aSec:Toggle({Title="Enable Aimbot", Default=false}, function(v) aimbotSettings.enabled = v applyAimbot() end)
aSec:Slider({Title="FOV Radius", Min=10, Max=500, Default=aimbotSettings.fov}, function(v) aimbotSettings.fov = v end)
aSec:Toggle({Title="Show FOV", Default=true}, function(v) aimbotSettings.showFov = v end)
aSec:ColorPicker({Title="FOV Color", Default=aimbotSettings.fovColor}, function(v) aimbotSettings.fovColor = v end)
aSec:Slider({Title="Smoothness", Min=0, Max=1, Default=aimbotSettings.smoothness}, function(v) aimbotSettings.smoothness = v end)
aSec:Toggle({Title="Team Check", Default=true}, function(v) aimbotSettings.teamCheck = v end)
aSec:Keybind({Title="Aimbot Key", Default=aimbotSettings.key}, function(v) aimbotSettings.key = v end)

local sSec = Aim:Button("Silent Aim", "http://www.roblox.com/asset/?id=8395747586"):Section("Silent Aim", "Left")
sSec:Toggle({Title="Enable Silent Aim", Default=false}, function(v) silentAimSettings.enabled = v applySilentAim() end)
sSec:Slider({Title="FOV Radius", Min=10, Max=500, Default=silentAimSettings.fov}, function(v) silentAimSettings.fov = v end)
sSec:Toggle({Title="Show FOV", Default=true}, function(v) silentAimSettings.showFov = v end)
sSec:Slider({Title="Smoothness", Min=0, Max=1, Default=silentAimSettings.smoothness}, function(v) silentAimSettings.smoothness = v end)
sSec:Toggle({Title="Team Check", Default=true}, function(v) silentAimSettings.teamCheck = v end)

--[[ MISC ]]--
local mSec = Misc:Button("Player Tweaks", "http://www.roblox.com/asset/?id=8395747586"):Section("Tweaks", "Left")
mSec:Slider({Title="WalkSpeed", Min=0, Max=300, Default=miscSettings.walkspeed}, function(v) miscSettings.walkspeed = v game.Players.LocalPlayer.Character.Humanoid.WalkSpeed = v end)
mSec:Slider({Title="JumpPower", Min=0, Max=300, Default=miscSettings.jumppower}, function(v) miscSettings.jumppower = v game.Players.LocalPlayer.Character.Humanoid.JumpPower = v end)
mSec:Slider({Title="Gravity", Min=0, Max=300, Default=miscSettings.gravity}, function(v) miscSettings.gravity = v game.Workspace.Gravity = v end)
mSec:Toggle({Title="Fly Mode", Default=false}, function(v) miscSettings.fly = v end)
mSec:Toggle({Title="NoClip Mode", Default=false}, function(v) miscSettings.noclip = v end)

--[[ SETTINGS ]]--
local setSec = Settings:Button("Painel", "http://www.roblox.com/asset/?id=8395747586"):Section("Configurações Gerais", "Left")
setSec:Keybind({Title="Toggle UI", Default=Enum.KeyCode.RightShift}, function(v) UILib:Toggle(v) end)
setSec:Button({Title="Salvar Perfil", ButtonName="Salvar"}, function() print("Salvar Config não implementado.") end)
setSec:Button({Title="Carregar Perfil", ButtonName="Carregar"}, function() print("Carregar Config não implementado.") end)
setSec:ColorPicker({Title="Cor Tema", Default=Color3.fromRGB(0, 255, 255)}, function(v) print("Trocar cor da UI não implementado.") end)
