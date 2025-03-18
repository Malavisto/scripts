-- Extreme Reactor Energy Monitor
-- For Minecraft 1.21.1
-- Monitors the energy buffer of an Extreme Reactor via computer port

-- Configuration
local REACTOR_SIDE = "back"  -- Side where the computer port is connected
local REFRESH_RATE = 1       -- Update interval in seconds
local MIN_ENERGY_PERCENT = 10 -- Minimum energy percentage before activating reactor
local MAX_ENERGY_PERCENT = 90 -- Maximum energy percentage before deactivating reactor
local AUTO_CONTROL = false    -- Set to true to enable automatic reactor control

-- Initialize peripherals
local reactor = peripheral.wrap(REACTOR_SIDE)
if not reactor then
  print("No reactor found on " .. REACTOR_SIDE .. " side")
  print("Please connect a reactor computer port and restart the program")
  return
end

-- Check if it's actually an Extreme Reactor
if not reactor.getConnected or not reactor.getEnergyStored then
  print("The connected peripheral is not an Extreme Reactor computer port")
  print("Please connect a valid reactor computer port and restart the program")
  return
end

-- Function to format numbers with commas
local function formatNumber(number)
  local formatted = tostring(number)
  local k
  while true do
    formatted, k = string.gsub(formatted, "^(-?%d+)(%d%d%d)", '%1,%2')
    if k == 0 then break end
  end
  return formatted
end

-- Function to format energy values (RF/FE)
local function formatEnergy(energy)
  if energy >= 1000000000 then
    return string.format("%.2f GRF", energy / 1000000000)
  elseif energy >= 1000000 then
    return string.format("%.2f MRF", energy / 1000000)
  elseif energy >= 1000 then
    return string.format("%.2f kRF", energy / 1000)
  else
    return string.format("%d RF", energy)
  end
end

-- Function to draw a progress bar
local function drawProgressBar(x, y, width, value, maxValue, color, backgroundColor)
  local percentage = value / maxValue
  local barWidth = math.floor(percentage * width)
  
  term.setBackgroundColor(backgroundColor)
  term.setCursorPos(x, y)
  term.write(string.rep(" ", width))
  
  term.setBackgroundColor(color)
  term.setCursorPos(x, y)
  term.write(string.rep(" ", barWidth))
  
  -- Reset colors
  term.setBackgroundColor(colors.black)
  term.setTextColor(colors.white)
end

-- Function to control the reactor based on energy levels
local function controlReactor(energyStored, energyCapacity)
  if not AUTO_CONTROL then return end
  
  local energyPercentage = (energyStored / energyCapacity) * 100
  
  if energyPercentage <= MIN_ENERGY_PERCENT and not reactor.getActive() then
    reactor.setActive(true)
    print("Reactor activated - Energy level low")
  elseif energyPercentage >= MAX_ENERGY_PERCENT and reactor.getActive() then
    reactor.setActive(false)
    print("Reactor deactivated - Energy level high")
  end
end

-- Main display function
local function displayInfo()
  term.clear()
  term.setCursorPos(1, 1)
  
  -- Get reactor information
  local active = reactor.getActive()
  local connected = reactor.getConnected()
  local energyStored = reactor.getEnergyStored()
  local energyCapacity = reactor.getEnergyCapacity()
  local energyPercentage = (energyStored / energyCapacity) * 100
  local fuelTemp = reactor.getFuelTemperature()
  local caseTemp = reactor.getCasingTemperature()
  local fuelLevel = reactor.getFuelAmount()
  local fuelCapacity = reactor.getFuelAmountMax()
  local fuelPercentage = (fuelLevel / fuelCapacity) * 100
  local energyProducedLastTick = reactor.getEnergyProducedLastTick()
  
  -- Display title
  term.setTextColor(colors.yellow)
  print("=== Extreme Reactor Monitor ===")
  term.setTextColor(colors.white)
  
  -- Display status
  print("Status: " .. (active and "ONLINE" or "OFFLINE"))
  print("Connected: " .. (connected and "Yes" or "No"))
  print("")
  
  -- Display energy information
  term.setTextColor(colors.cyan)
  print("Energy Buffer:")
  term.setTextColor(colors.white)
  print("Stored: " .. formatEnergy(energyStored) .. " / " .. formatEnergy(energyCapacity) .. 
        " (" .. string.format("%.1f%%", energyPercentage) .. ")")
  
  -- Draw energy bar
  local barColor = colors.green
  if energyPercentage < 25 then
    barColor = colors.red
  elseif energyPercentage < 50 then
    barColor = colors.orange
  end
  
  drawProgressBar(2, 7, 36, energyStored, energyCapacity, barColor, colors.gray)
  print("")
  
  -- Display generation rate
  print("Generation: " .. formatEnergy(energyProducedLastTick) .. "/t")
  print("")
  
  -- Display temperature information
  term.setTextColor(colors.cyan)
  print("Temperature:")
  term.setTextColor(colors.white)
  print("Fuel: " .. string.format("%.1f C", fuelTemp))
  print("Casing: " .. string.format("%.1f C", caseTemp))
  print("")
  
  -- Display fuel information
  term.setTextColor(colors.cyan)
  print("Fuel:")
  term.setTextColor(colors.white)
  print("Level: " .. string.format("%.1f%%", fuelPercentage))
  
  -- Draw fuel bar
  local fuelBarColor = colors.yellow
  if fuelPercentage < 15 then
    fuelBarColor = colors.red
  end
  
  drawProgressBar(2, 16, 36, fuelLevel, fuelCapacity, fuelBarColor, colors.gray)
  print("")
  
  -- Display controls
  term.setTextColor(colors.lime)
  print("Controls:")
  term.setTextColor(colors.white)
  print("T - Toggle reactor on/off")
  print("A - Toggle auto control: " .. (AUTO_CONTROL and "ON" or "OFF"))
  print("Q - Quit")
  
  -- Control the reactor if auto control is enabled
  controlReactor(energyStored, energyCapacity)
end

-- Main loop
local function main()
  local running = true
  
  -- Start parallel event handling
  parallel.waitForAny(
    -- Display update loop
    function()
      while running do
        displayInfo()
        sleep(REFRESH_RATE)
      end
    end,
    
    -- Input handling
    function()
      while running do
        local event, key = os.pullEvent("key")
        
        if key == keys.t then
          reactor.setActive(not reactor.getActive())
          displayInfo()
        elseif key == keys.a then
          AUTO_CONTROL = not AUTO_CONTROL
          displayInfo()
        elseif key == keys.q then
          running = false
          term.clear()
          term.setCursorPos(1, 1)
          print("Reactor monitor terminated")
        end
      end
    end
  )
end

-- Run the program
main()