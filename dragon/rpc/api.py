# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

ENGINE_TOPIC = 'dr-engine'

PARAM_KEYS = (
    PARAM_TIMEOUT, PARAM_DISABLE_ROLLBACK
) = (
    'timeout_mins', 'disable_rollback'
)

VALIDATE_PARAM_KEYS = (
    PARAM_TYPE, PARAM_DEFAULT, PARAM_NO_ECHO,
    PARAM_ALLOWED_VALUES, PARAM_ALLOWED_PATTERN, PARAM_MAX_LENGTH,
    PARAM_MIN_LENGTH, PARAM_MAX_VALUE, PARAM_MIN_VALUE,
    PARAM_DESCRIPTION, PARAM_CONSTRAINT_DESCRIPTION
) = (
    'Type', 'Default', 'NoEcho',
    'AllowedValues', 'AllowedPattern', 'MaxLength',
    'MinLength', 'MaxValue', 'MinValue',
    'Description', 'ConstraintDescription'
)
