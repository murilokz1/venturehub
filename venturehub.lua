local UILib = loadstring(game:HttpGet('https://raw.githubusercontent.com/StepBroFurious/Script/main/HydraHubUi.lua'))()
local Window = UILib.new("VentureHub", game.Players.LocalPlayer.UserId, "Dev Build")

-- 🟠 Categoria Principal
local CategoryMain = Window:Category("Main", "http://www.roblox.com/asset/?id=8395621517")

-- 🟥 Sessão de Aimbot
local SubCombat = CategoryMain:Button("Aimbot", "http://www.roblox.com/asset/?id=8395747586")
local SectionAimbot = SubCombat:Section("Aimbot", "Left")

SectionAimbot:Toggle({
    Title = "Enable Aimbot",
    Description = "Trava a mira no inimigo mais próximo",
    Default = false,
}, function(enabled)
    local Players = game:GetService("Players")
    local UserInputService = game:GetService("UserInputService")
    local LocalPlayer = Players.LocalPlayer
    local Camera = workspace.CurrentCamera

    local function getClosestEnemy()
        local closest, dist = nil, math.huge
        for _, player in pairs(Players:GetPlayers()) do
            if player ~= LocalPlayer and player.Character and player.Character:FindFirstChild("Head") then
                local screenPos, onScreen = Camera:WorldToViewportPoint(player.Character.Head.Position)
                if onScreen then
                    local mousePos = UserInputService:GetMouseLocation()
                    local d = (Vector2.new(screenPos.X, screenPos.Y) - mousePos).Magnitude
                    if d < dist then
                        dist = d
                        closest = player
                    end
                end
            end
        end
        return closest
    end

    if enabled then
        UserInputService.InputBegan:Connect(function(input)
            if input.UserInputType == Enum.UserInputType.MouseButton2 then
                local target = getClosestEnemy()
                if target and target.Character and target.Character:FindFirstChild("Head") then
                    Camera.CFrame = CFrame.new(Camera.CFrame.Position, target.Character.Head.Position)
                end
            end
        end)
    end
end)

-- 🟦 Sessão de ESP
local SubESP = CategoryMain:Button("ESP", "http://www.roblox.com/asset/?id=8395747586")
local SectionESP = SubESP:Section("ESP", "Left")

SectionESP:Button({
    Title = "Ativar ESP",
    ButtonName = "ESP ON",
    Description = "Mostra nome dos jogadores na cabeça",
}, function()
    local Players = game:GetService("Players")
    local LocalPlayer = Players.LocalPlayer

    local function createESP(player)
        if player == LocalPlayer then return end
        local char = player.Character or player.CharacterAdded:Wait()
        local head = char:WaitForChild("Head")
        if head:FindFirstChild("ESP") then return end

        local billboard = Instance.new("BillboardGui", head)
        billboard.Name = "ESP"
        billboard.Size = UDim2.new(0, 100, 0, 40)
        billboard.AlwaysOnTop = true

        local nameLabel = Instance.new("TextLabel", billboard)
        nameLabel.Size = UDim2.new(1, 0, 1, 0)
        nameLabel.BackgroundTransparency = 1
        nameLabel.TextColor3 = Color3.new(1, 0, 0)
        nameLabel.Text = player.Name
    end

    for _, player in ipairs(Players:GetPlayers()) do
        createESP(player)
    end

    Players.PlayerAdded:Connect(createESP)
end)

-- 🟩 Sessão de Silent Aim
local SubSilent = CategoryMain:Button("Silent Aim", "http://www.roblox.com/asset/?id=8395747586")
local SectionSilent = SubSilent:Section("Silent Aim", "Left")

SectionSilent:Toggle({
    Title = "Enable Silent Aim",
    Description = "Redireciona tiros silenciosamente para o inimigo mais próximo",
    Default = false,
}, function(enabled)
    local Players = game:GetService("Players")
    local LocalPlayer = Players.LocalPlayer

    local function getSilentAimTarget()
        for _, player in ipairs(Players:GetPlayers()) do
            if player ~= LocalPlayer and player.Character and player.Character:FindFirstChild("Head") then
                return player.Character.Head
            end
        end
    end

    if enabled then
        print("Silent Aim ON")
        -- Substitua isso com o evento de tiro real usado no seu jogo
        game:GetService("ReplicatedStorage").RemoteEvent.OnClientEvent:Connect(function()
            local target = getSilentAimTarget()
            if target then
                print("Silent Aim redirecionado para:", target.Parent.Name)
                -- Aqui você poderia redirecionar um tiro, dependendo do sistema de combate usado
            end
        end)
    end
end)