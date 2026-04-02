# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for template_library.py."""

from demos.backend.ads_x_template.utils.storyboard.template_library import (
    get_all_templates,
    get_template_by_name,
    suggest_template,
)


def test_get_all_templates():
    templates = get_all_templates()
    assert len(templates) > 0


def test_get_template_by_name():
    templates = get_all_templates()
    first_name = templates[0].template_name
    
    # Success
    t = get_template_by_name(first_name)
    assert t.template_name == first_name
    
    # Fallback
    t_fallback = get_template_by_name("NonExistentTemplate")
    assert t_fallback is not None


def test_suggest_template_industry_only():
    # Success
    t = suggest_template("social native")
    assert t is not None
    
    t_default = suggest_template("random")
    assert t_default is not None


def test_suggest_template_vertical():
    # UGC
    t = suggest_template("", "tiktok")
    assert t is not None
    
    t_unboxing = suggest_template("", "tiktok unboxing")
    assert t_unboxing is not None
    
    t_impression = suggest_template("", "tiktok impression")
    assert t_impression is not None
    
    # Pet
    t_pet = suggest_template("", "pet")
    assert t_pet.vertical_category == "Pets"
    
    # Apparel
    t_apparel = suggest_template("", "fashion")
    assert t_apparel.vertical_category == "Apparel"
    
    # Beauty
    t_beauty = suggest_template("", "beauty")
    assert t_beauty.vertical_category == "Beauty"
    
    # Home
    t_home = suggest_template("", "home")
    assert t_home.vertical_category == "Home"
    
    # Food
    t_food = suggest_template("", "meal")
    assert t_food.vertical_category == "Food & Beverage"
    
    # Default
    t_default = suggest_template("", "random")
    assert t_default is not None
