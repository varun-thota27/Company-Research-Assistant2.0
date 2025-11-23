class PlanEditor:
    def edit_section(self, plan, section, new_text):
        if section not in plan:
            return "Section does not exist."
        plan[section] = new_text
        return "Section updated successfully."
