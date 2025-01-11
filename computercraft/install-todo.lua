-- Todo List Installer

local function downloadFile(url, path)
    -- Delete existing file if it exists
    if fs.exists(path) then
        fs.delete(path)
    end
    
    -- Download the new file
    shell.run("wget", url, path)
    
    if not fs.exists(path) then
        error("Failed to download " .. path)
    end
    
    print("Successfully downloaded " .. path)
end

-- Replace this URL with your actual GitHub raw file URL
local todoUrl = "https://raw.githubusercontent.com/malavisto/scripts/main/computercraft/todo.lua"

print("Installing Todo List program...")
downloadFile(todoUrl, "todo")
shell.run("chmod +x todo")
print("Installation complete! Run 'todo' to start the program")