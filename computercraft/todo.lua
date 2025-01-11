-- Todo List Program for ComputerCraft
local todos = {}
local filename = "todos.txt"

-- Load existing todos from file
local function loadTodos()
    if fs.exists(filename) then
        local file = fs.open(filename, "r")
        local content = file.readAll()
        file.close()
        
        if content then
            todos = textutils.unserialize(content) or {}
        end
    end
end

-- Save todos to file
local function saveTodos()
    local file = fs.open(filename, "w")
    file.write(textutils.serialize(todos))
    file.close()
end

-- Add a new todo
local function addTodo()
    term.clear()
    term.setCursorPos(1,1)
    print("Enter your todo (press Enter when done):")
    local input = read()
    if input ~= "" then
        table.insert(todos, {text = input, completed = false})
        saveTodos()
        print("Todo added!")
        sleep(1)
    end
end

-- View all todos
local function viewTodos()
    term.clear()
    term.setCursorPos(1,1)
    print("Your Todo List:")
    print("---------------")
    
    for i, todo in ipairs(todos) do
        local status = todo.completed and "[X]" or "[ ]"
        print(i .. ". " .. status .. " " .. todo.text)
    end
    
    print("\nPress any key to continue...")
    os.pullEvent("key")
end

-- Toggle todo completion
local function toggleTodo()
    term.clear()
    term.setCursorPos(1,1)
    print("Enter the number of the todo to toggle:")
    local input = tonumber(read())
    
    if input and todos[input] then
        todos[input].completed = not todos[input].completed
        saveTodos()
        print("Todo status toggled!")
        sleep(1)
    else
        print("Invalid todo number!")
        sleep(1)
    end
end

-- Remove a todo
local function removeTodo()
    term.clear()
    term.setCursorPos(1,1)
    print("Enter the number of the todo to remove:")
    local input = tonumber(read())
    
    if input and todos[input] then
        table.remove(todos, input)
        saveTodos()
        print("Todo removed!")
        sleep(1)
    else
        print("Invalid todo number!")
        sleep(1)
    end
end

-- Main program loop
local function main()
    loadTodos()
    
    while true do
        term.clear()
        term.setCursorPos(1,1)
        print("Todo List Manager")
        print("-----------------")
        print("1. Add Todo")
        print("2. View Todos")
        print("3. Toggle Todo")
        print("4. Remove Todo")
        print("5. Exit")
        print("\nEnter your choice (1-5):")
        
        local choice = read()
        
        if choice == "1" then
            addTodo()
        elseif choice == "2" then
            viewTodos()
        elseif choice == "3" then
            toggleTodo()
        elseif choice == "4" then
            removeTodo()
        elseif choice == "5" then
            term.clear()
            term.setCursorPos(1,1)
            print("Goodbye!")
            return
        end
    end
end

-- Start the program
main()