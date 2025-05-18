-- UI LIB
local UILib = loadstring(game:HttpGet('https://raw.githubusercontent.com/StepBroFurious/Script/main/HydraHubUi.lua'))()
local Window = UILib.new("VentureHub", game.Players.LocalPlayer.UserId, "nigga")

-- Mostrar/esconder UI com tecla
local UserInputService = game:GetService("UserInputService")
local toggleKey = Enum.KeyCode.RightShift

UserInputService.InputBegan:Connect(function(input, gameProcessed)
    if input.KeyCode == toggleKey and not gameProcessed then
        if Window and Window.Gui then
            Window.Gui.Enabled = not Window.Gui.Enabled
        end
    end
end)

-- CATEGORIA PRINCIPAL
local CategoryMain = Window:Category("Main", "http://www.roblox.com/asset/?id=8395621517")

--------------------------------------------------------
---------------------- ESP PANEL -----------------------
--------------------------------------------------------

local SubESP = CategoryMain:Button("ESP", "http://www.roblox.com/asset/?id=8395747586")
local SectionESP = SubESP:Section("ESP Options", "Left")

local ESP_Enabled = false
local ShowNames = false
local ShowBoxes = false
local ShowLines = false
local ESP_Connections = {}
local ESP_Objects = {}

local function clearESP()
    for _, v in pairs(ESP_Objects) do
        if v and typeof(v) == "Instance" then
            v:Destroy()
        elseif typeof(v) == "table" then
            for _, obj in pairs(v) do
                if obj and obj.Destroy then
                    obj:Destroy()
                end
            end
        end
    end
    ESP_Objects = {}
end

local function applyESP(player)
    local Camera = workspace.CurrentCamera
    local LocalPlayer = game.Players.LocalPlayer
    if player == LocalPlayer or not player.Character or not player.Character:FindFirstChild("Head") then return end

    local char = player.Character
    local head = char:FindFirstChild("Head")
    local Billboard, Tracer, Box

    if ShowNames then
        Billboard = Instance.new("BillboardGui", head)
        Billboard.Name = "ESPName"
        Billboard.Size = UDim2.new(0, 100, 0, 40)
        Billboard.AlwaysOnTop = true

        local nameLabel = Instance.new("TextLabel", Billboard)
        nameLabel.Size = UDim2.new(1, 0, 1, 0)
        nameLabel.BackgroundTransparency = 1
        nameLabel.TextColor3 = Color3.new(1, 0, 0)
        nameLabel.Text = player.Name
    end

    if ShowLines then
        Tracer = Instance.new("Beam", Camera)
        local att0 = Instance.new("Attachment", Camera)
        local att1 = Instance.new("Attachment", head)

        Tracer.Attachment0 = att0
        Tracer.Attachment1 = att1
        Tracer.Color = ColorSequence.new(Color3.new(1, 0, 0))
        Tracer.Width0 = 0.05
        Tracer.Width1 = 0.05
        Tracer.FaceCamera = true
    end

    if ShowBoxes then
        Box = Instance.new("BoxHandleAdornment", head)
        Box.Adornee = char
        Box.Size = char:GetExtentsSize()
        Box.AlwaysOnTop = true
        Box.ZIndex = 5
        Box.Color3 = Color3.fromRGB(255, 0, 0)
        Box.Transparency = 0.5
    end

    ESP_Objects[player] = {Billboard = Billboard, Tracer = Tracer, Box = Box}
end

local function updateESP()
    clearESP()
    for _, player in ipairs(game.Players:GetPlayers()) do
        applyESP(player)
    end
end

SectionESP:Toggle({ Title = "Enable ESP", Description = "Ativa/Desativa todo o sistema ESP", Default = false }, function(state)
    ESP_Enabled = state
    if state then
        updateESP()
        table.insert(ESP_Connections, game.Players.PlayerAdded:Connect(function(p) task.wait(1) applyESP(p) end))
        table.insert(ESP_Connections, game.Players.PlayerRemoving:Connect(function(p) clearESP() end))
    else
        clearESP()
        for _, con in ipairs(ESP_Connections) do con:Disconnect() end
        ESP_Connections = {}
    end
end)

SectionESP:Toggle({ Title = "Show Names", Description = "Mostra nomes dos jogadores", Default = false }, function(val)
    ShowNames = val
    if ESP_Enabled then updateESP() end
end)

SectionESP:Toggle({ Title = "Show Boxes", Description = "Mostra caixas ao redor do jogador", Default = false }, function(val)
    ShowBoxes = val
    if ESP_Enabled then updateESP() end
end)

SectionESP:Toggle({ Title = "Show Lines", Description = "Desenha linhas da câmera até o jogador", Default = false }, function(val)
    ShowLines = val
    if ESP_Enabled then updateESP() end
end)

--------------------------------------------------------
--------------------- AIMBOT PANEL ---------------------
--------------------------------------------------------

local SubAimbot = CategoryMain:Button("Aimbot", "http://www.roblox.com/asset/?id=8395747586")
local SectionAimbot = SubAimbot:Section("Aimbot Settings", "Left")

local Aimbot_Enabled = false
local Aimbot_FOV = 100
local Aimbot_ShowFOV = false
local Aimbot_Smoothness = 0.1
local Aimbot_Key = Enum.UserInputType.MouseButton2

local RunService = game:GetService("RunService")
local Players = game:GetService("Players")
local Camera = workspace.CurrentCamera
local LocalPlayer = Players.LocalPlayer
local FOVCircle

local function drawFOV()
    if FOVCircle then FOVCircle:Remove() end
    FOVCircle = Drawing.new("Circle")
    FOVCircle.Color = Color3.fromRGB(255, 255, 0)
    FOVCircle.Thickness = 1
    FOVCircle.NumSides = 100
    FOVCircle.Radius = Aimbot_FOV
    FOVCircle.Filled = false
    FOVCircle.Visible = Aimbot_ShowFOV
end

local function getClosestTarget()
    local closest = nil
    local shortestDist = Aimbot_FOV

    for _, player in ipairs(Players:GetPlayers()) do
        if player ~= LocalPlayer and player.Character and player.Character:FindFirstChild("Head") then
            local pos, onScreen = Camera:WorldToViewportPoint(player.Character.Head.Position)
            if onScreen then
                local mousePos = UserInputService:GetMouseLocation()
                local dist = (Vector2.new(pos.X, pos.Y) - mousePos).Magnitude
                if dist < shortestDist then
                    shortestDist = dist
                    closest = player
                end
            end
        end
    end

    return closest
end

RunService.RenderStepped:Connect(function()
    if Aimbot_Enabled and UserInputService:IsMouseButtonPressed(Enum.UserInputType.MouseButton2) then
        local target = getClosestTarget()
        if target and target.Character and target.Character:FindFirstChild("Head") then
            local targetPos = target.Character.Head.Position
            local camPos = Camera.CFrame.Position
            local direction = (targetPos - camPos).Unit
            local newLook = camPos + direction * Aimbot_Smoothness
            Camera.CFrame = CFrame.new(camPos, newLook)
        end
    end

    if FOVCircle and Aimbot_ShowFOV then
        local mouse = UserInputService:GetMouseLocation()
        FOVCircle.Position = Vector2.new(mouse.X, mouse.Y)
    end
end)

SectionAimbot:Toggle({ Title = "Enable Aimbot", Description = "Liga ou desliga o Aimbot", Default = false }, function(state)
    Aimbot_Enabled = state
end)

SectionAimbot:Slider({ Title = "FOV Radius", Description = "Área de detecção de inimigos", Default = 100, Min = 10, Max = 500 }, function(val)
    Aimbot_FOV = val
    if FOVCircle then FOVCircle.Radius = val end
end)

SectionAimbot:Toggle({ Title = "Show FOV Circle", Description = "Mostra o círculo FOV ao redor do cursor", Default = false }, function(val)
    Aimbot_ShowFOV = val
    drawFOV()
end)

SectionAimbot:Slider({ Title = "Aimbot Smoothness", Description = "Velocidade da mira (0.1 = rápido, 1 = lento)", Default = 0.1, Min = 0.05, Max = 1 }, function(val)
    Aimbot_Smoothness = val
end)

SectionAimbot:Keybind({ Title = "Aimbot Key", Description = "Tecla para ativar o Aimbot", Default = Enum.KeyCode.Q }, function(val)
    Aimbot_Key = val
end)
